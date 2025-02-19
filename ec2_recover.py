# AWS EC2 Recovery Tool, v2 AUTHOR: michael.quintero@rackspace.com
# PURPOSE: To rebuild EC2 instances using the create-replace-root-volume-task action, now processes batches of instances in parallel. 
# The user is presented with 3 options:
#   1) Replace the root volume using a specific snapshot that the user provides
#   2) Restore the root device from a specific AMI
#   3) Batch process recovery for multiple instances in parallel, using the most recent AMI or snapshot. 
# Additional Info: https://docs.aws.amazon.com/cli/latest/reference/ec2/create-replace-root-volume-task.html
# Additional Info: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/replace-root.html
# Usage: python3 ec2_recover.py, answer the questions (Understand disclaimer, set the region, select the option), bam!
# Note: User is expected to have already set credentials. Requirements are boto3 & colorama. Original volumes are detached and NOT deleted!
# Warning: If using option 3, the file MUST HAVE INSTANCE IDS, one per line. The script will skip empty lines and invalid IDs!

import boto3
import time
import os
import concurrent.futures
from datetime import datetime
from colorama import Fore, Style, init

def print_disclaimer():
    """
    Used the colorama library to improve readability, but may end up removing to keep the script tight. Here, we display a disclaimer because people need to know!
    """
    print(Fore.RED + "#####################################################################")
    print(Fore.RED + "#                           DISCLAIMER                              #")
    print(Fore.RED + "#####################################################################")
    print("WARNING: This tool can perform DESTRUCTIVE operations.")
    print("By using this tool, YOU ACKNOWLEDGE AND AGREE that:")
    print("1. You have full knowledge of the actions this tool will perform.")
    print("2. You accept all liability for the use of this tool.")
    print("   This action CANNOT BE UNDONE.")
    print(Fore.RED + "#####################################################################")
    print(Style.RESET_ALL)

def replace_root_volume(instance_id, snapshot_id, ec2):
    """
    Create the replace root volume task using a snapshot. Here we creates a replace root volume task, waits for completion, and logs progress. Still looking into cloudtrails options for an easy search in regards to the taskid
    Args:
        instance_id (str): The ID of the EC2 instance.
        snapshot_id (str): The ID of the snapshot to restore from.
        ec2 (boto3.client): The EC2 client instance. 
    """
    print(Fore.CYAN + f"Creating replace root volume task for instance {instance_id} with snapshot {snapshot_id}..." + Style.RESET_ALL)

    response = ec2.create_replace_root_volume_task(
        InstanceId=instance_id,
        SnapshotId=snapshot_id
    )
    task_id = response['ReplaceRootVolumeTask']['ReplaceRootVolumeTaskId']
    print(Fore.GREEN + f"Created replace root volume task with ID: {task_id}" + Style.RESET_ALL)

    # Waiting for the replace root task to complete. Added to ease the nerves of the user, they can leave it on screen until it completes.
    while True:
        task_status = ec2.describe_replace_root_volume_tasks(
            ReplaceRootVolumeTaskIds=[task_id]
        )['ReplaceRootVolumeTasks'][0]['TaskState']

        if task_status in ['completed', 'failed', 'succeeded']:
            break
        print(Fore.YELLOW + f"Waiting for replace root volume task {task_id} to complete (current state: {task_status})" + Style.RESET_ALL)
        time.sleep(10)

    if task_status in ['succeeded', 'completed']:
        print(Fore.GREEN + f"Replace root volume task {task_id} completed successfully." + Style.RESET_ALL)
    else:
        print(Fore.RED + f"Replace root volume task {task_id} failed." + Style.RESET_ALL)

def get_latest_ami(instance_id, ec2):
    """
    Looking for the most recent AMI backup for each instance. We'll starting with listing all of them...
    Args:
        instance_id (str): The ID of the EC2 instance.
        ec2 (boto3.client): The EC2 client instance.

    Returns:
        str or None: The latest AMI ID if found, otherwise None.
    """
    try:
        print(Fore.CYAN + f"Searching for the most recent AMI for instance {instance_id}..." + Style.RESET_ALL)

        # Retrieve all AMIs owned by the account
        images = ec2.describe_images(Owners=['self'])['Images']

        instance_amis = []

        # First attempt: Find AMIs linked via snapshot history
        for image in images:
            if 'BlockDeviceMappings' in image:
                for block_device in image['BlockDeviceMappings']:
                    if 'Ebs' in block_device and 'SnapshotId' in block_device['Ebs']:
                        snapshot_id = block_device['Ebs']['SnapshotId']

                        try:
                            snapshots = ec2.describe_snapshots(SnapshotIds=[snapshot_id])['Snapshots']
                            if snapshots and snapshots[0]['Description'].startswith(f"Created by CreateImage for {instance_id}"):
                                instance_amis.append(image)
                        except Exception as e:
                            print(Fore.YELLOW + f"Warning: Could not verify snapshot {snapshot_id} for AMI {image['ImageId']}: {e}" + Style.RESET_ALL)

        # If we found an AMI via snapshot validation, use it
        if instance_amis:
            latest_ami = sorted(instance_amis, key=lambda x: x['CreationDate'], reverse=True)[0]
            ami_id = latest_ami['ImageId']
            creation_date = latest_ami['CreationDate']
            print(Fore.GREEN + f"Using AMI for instance {instance_id}: {ami_id} (Created: {creation_date})" + Style.RESET_ALL)
            return ami_id

        # SECONDARY SEARCH: Find AMIs using naming pattern only if no snapshot-linked AMI exists
        filtered_amis = [
            image for image in images if instance_id in image['Name']
        ]

        if filtered_amis:
            latest_ami = sorted(filtered_amis, key=lambda x: x['CreationDate'], reverse=True)[0]
            ami_id = latest_ami['ImageId']
            creation_date = latest_ami['CreationDate']

            # Print fallback message **only if no snapshot-linked AMI was found**
            print(Fore.GREEN + f"Using AMI found via instance name pattern for instance {instance_id}: {ami_id} (Created: {creation_date})" + Style.RESET_ALL)
            return ami_id

        print(Fore.YELLOW + f"No AMIs found for instance {instance_id}. Skipping." + Style.RESET_ALL)
        return None

    except Exception as e:
        print(Fore.RED + f"Error retrieving AMI for instance {instance_id}: {e}" + Style.RESET_ALL)
        return None

def restore_from_ami(instance_id, ami_id, ec2):
    """
    Performs an in-place recovery of an EC2 instance from a given AMI by replacing its root volume. This is a destructive operation & should be used with caution!
    """
    try:
        print(Fore.CYAN + f"Stopping instance {instance_id}..." + Style.RESET_ALL)
        ec2.stop_instances(InstanceIds=[instance_id])
        ec2.get_waiter('instance_stopped').wait(InstanceIds=[instance_id])
        print(Fore.GREEN + f"Instance {instance_id} is now stopped." + Style.RESET_ALL)

        # Pulling AMI deets
        ami_info = ec2.describe_images(ImageIds=[ami_id])['Images'][0]
        root_snapshot_id = ami_info['BlockDeviceMappings'][0]['Ebs']['SnapshotId']
        root_device_name = ami_info['BlockDeviceMappings'][0]['DeviceName']

        # Pulling current instance deets
        instance_info = ec2.describe_instances(InstanceIds=[instance_id])['Reservations'][0]['Instances'][0]
        old_root_volume_id = instance_info['BlockDeviceMappings'][0]['Ebs']['VolumeId']
        availability_zone = instance_info['Placement']['AvailabilityZone']

        print(Fore.CYAN + f"Detaching old root volume {old_root_volume_id} from {instance_id}..." + Style.RESET_ALL)
        ec2.detach_volume(VolumeId=old_root_volume_id, InstanceId=instance_id, Device=root_device_name)
        # This sleep, is to allow time for detachment
        time.sleep(10)  

        print(Fore.CYAN + f"Creating a new root volume from snapshot {root_snapshot_id} in {availability_zone}..." + Style.RESET_ALL)
        new_volume = ec2.create_volume(
            SnapshotId=root_snapshot_id,
            AvailabilityZone=availability_zone,
            VolumeType="gp3"
        )

        new_volume_id = new_volume['VolumeId']
        print(Fore.GREEN + f"New root volume created: {new_volume_id}" + Style.RESET_ALL)

        # More waiting, this time for the volume to become available
        ec2.get_waiter('volume_available').wait(VolumeIds=[new_volume_id])

        print(Fore.CYAN + f"Attaching new root volume {new_volume_id} to instance {instance_id}..." + Style.RESET_ALL)
        ec2.attach_volume(
            VolumeId=new_volume_id,
            InstanceId=instance_id,
            Device=root_device_name
        )
        # This sleep, is to allow time for attachment. Some sleeps are unnecessary, so I try adding them when they are functional.
        time.sleep(10)  

        print(Fore.CYAN + f"Starting instance {instance_id}..." + Style.RESET_ALL)
        ec2.start_instances(InstanceIds=[instance_id])
        ec2.get_waiter('instance_running').wait(InstanceIds=[instance_id])

        print(Fore.GREEN + f"Instance {instance_id} has been successfully restored using AMI {ami_id}!" + Style.RESET_ALL)

    except Exception as e:
        print(Fore.RED + f"Failed to restore instance {instance_id} from AMI {ami_id}: {e}" + Style.RESET_ALL)

def batch_process_recovery(ec2):
    """
    Here's where I got excited! The request I had was to update the rool to recover multiple instances by replacing root volumes using their own historical snapshots (Now Runs in Parallel using the concurrent.futures module!!!).    
    Args:
        ec2 (boto3.client): The EC2 client instance.
    """
    file_path = input("Enter the path to the file containing instance IDs: ").strip()
    if not os.path.exists(file_path):
        print(Fore.RED + "File not found. Exiting." + Style.RESET_ALL)
        return

    with open(file_path, 'r') as file:
        instance_ids = [line.strip() for line in file if line.strip()]

    if not instance_ids:
        print(Fore.RED + "No valid instance IDs found in the file. Exiting." + Style.RESET_ALL)
        return

    print(Fore.CYAN + f"Starting parallel recovery for {len(instance_ids)} instances..." + Style.RESET_ALL)

    instance_results = {}  # Store the recovery details for each instance

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_instance = {
            executor.submit(recover_instance, instance_id, ec2): instance_id
            for instance_id in instance_ids
        }

        for future in concurrent.futures.as_completed(future_to_instance):
            instance_id = future_to_instance[future]
            try:
                instance_id, recovery_type, resource_id = future.result()
                instance_results[instance_id] = (recovery_type, resource_id)
            except Exception as e:
                instance_results[instance_id] = ("FAILED", str(e))

    print(Fore.GREEN + "Batch processing completed.\n" + Style.RESET_ALL)
    
    # Perform final status check
    print(Fore.CYAN + "Final instance recovery summary:" + Style.RESET_ALL)
    for instance_id, (recovery_type, resource_id) in instance_results.items():
        print(f"{Fore.YELLOW}Instance {instance_id}: {recovery_type} - {resource_id}{Style.RESET_ALL}")
    
    print(Fore.CYAN + "\nChecking final instance states..." + Style.RESET_ALL)
    for instance_id in instance_ids:
        instance_state = check_instance_status(instance_id, ec2)
        print(Fore.GREEN + f"Instance {instance_id} final state: {instance_state}" + Style.RESET_ALL)

def check_instance_status(instance_id, ec2):
    """
    Retrieves the current state of an EC2 instance.
    Args:
        instance_id (str): The ID of the EC2 instance.
        ec2 (boto3.client): The EC2 client instance.
    
    Returns:
        str: The current state of the instance.
    """
    try:
        response = ec2.describe_instances(InstanceIds=[instance_id])
        state = response['Reservations'][0]['Instances'][0]['State']['Name']
        return state.upper()
    except Exception as e:
        return f"ERROR: {e}"

def recover_instance(instance_id, ec2):
    """
    Attempt to recover an EC2 instance using the latest AMI or snapshot.
    We're attempting to recover an EC2 instance by restoring from an AMI or a snapshot, depending on availability.
    Args:
        instance_id (str): The ID of the EC2 instance.
        ec2 (boto3.client): The EC2 client instance.

    Returns:
        tuple: (instance_id, "AMI Used" or "Snapshot Used", resource_id)
    """
    print(Fore.CYAN + f"Processing recovery for instance: {instance_id}" + Style.RESET_ALL)

    # Step 1: Look for the latest AMI first
    ami_id = get_latest_ami(instance_id, ec2)
    if ami_id:
        print(Fore.CYAN + f"Using AMI {ami_id} for recovery of instance {instance_id}..." + Style.RESET_ALL)
        restore_from_ami(instance_id, ami_id, ec2)
        return (instance_id, "AMI Used", ami_id)  # Return the AMI used for logging

    # Step 2: If no AMI found, fallback to using snapshots
    snapshot_id = get_latest_snapshot(instance_id, ec2)
    if snapshot_id:
        print(Fore.CYAN + f"Using snapshot {snapshot_id} for recovery of instance {instance_id}..." + Style.RESET_ALL)
        replace_root_volume(instance_id, snapshot_id, ec2)
        return (instance_id, "Snapshot Used", snapshot_id)  # Return snapshot ID

    # Step 3: No recovery method found
    print(Fore.YELLOW + f"No AMI or valid snapshot found for instance {instance_id}. Skipping recovery." + Style.RESET_ALL)
    return (instance_id, "FAILED", "No Recovery Resource Found")

def get_latest_snapshot(instance_id, ec2):
    """
    Now, we look for the most recent snapshot from any root volume previously attached to the instance. I'm still thinking about how to finalize this portion of the function. I picked ANY for testing, but....I'm thinking more like adding logic to increment days backward and iterate through the snapshots.
    """
    try:
        print(Fore.CYAN + f"Retrieving snapshot history for instance {instance_id}..." + Style.RESET_ALL)

        # Get all volume history for the instance (including past root volumes)
        volumes = ec2.describe_volumes(
            Filters=[{'Name': 'attachment.instance-id', 'Values': [instance_id]}]
        )['Volumes']

        if not volumes:
            print(Fore.YELLOW + f"No historical volumes found for instance {instance_id}. Skipping." + Style.RESET_ALL)
            return None

        # Gather all past volume IDs
        volume_ids = [vol['VolumeId'] for vol in volumes]

        # Find snapshots for any past root volume
        snapshots = ec2.describe_snapshots(
            Filters=[
                {'Name': 'volume-id', 'Values': volume_ids},  # Search across all historical root volumes
                {'Name': 'status', 'Values': ['completed']}
            ]
        )['Snapshots']

        if not snapshots:
            print(Fore.YELLOW + f"No valid snapshots found for instance {instance_id}. Skipping." + Style.RESET_ALL)
            return None

        # Sort snapshots by creation date (latest first)
        latest_snapshot = sorted(snapshots, key=lambda x: x['StartTime'], reverse=True)[0]
        snapshot_id = latest_snapshot['SnapshotId']
        snapshot_creation_date = latest_snapshot['StartTime'].strftime("%Y-%m-%d %H:%M:%S UTC")

        print(Fore.GREEN + f"Found valid snapshot for instance {instance_id}: {snapshot_id} (Created: {snapshot_creation_date})" + Style.RESET_ALL)
        return snapshot_id

    except Exception as e:
        print(Fore.RED + f"Error fetching snapshot for instance {instance_id}: {e}" + Style.RESET_ALL)
        return None

if __name__ == "__main__":
    init(autoreset=True)  # Enable colorama for colored output. Improves readability so much.

    print_disclaimer()
    agreement = input("Your choice (I AGREE/EXIT): ").strip().upper()
    if agreement != "I AGREE":
        print("Exiting tool. No actions have been performed.")
        exit(0)

    region = input("Enter AWS region: ").strip()
    ec2 = boto3.client('ec2', region_name=region)

    action = input("Do you want to (1) replace root volume using a snapshot, (2) restore from AMI backup, or (3) batch process recovery? Enter 1, 2, or 3: ").strip()

    if action == '1':
        instance_id = input("Enter the instance ID: ").strip()
        snapshot_id = input("Enter the snapshot ID: ").strip()
        replace_root_volume(instance_id, snapshot_id, ec2)

    elif action == '2':
        instance_id = input("Enter the instance ID: ").strip()  # Prompting for an instance ID
        ami_id = input("Enter the AMI ID: ").strip()
        restore_from_ami(instance_id, ami_id, ec2)  # Only passing the required arguments. I reworked this function for modularity.

    elif action == '3':
        batch_process_recovery(ec2)

    else:
        print("Invalid option. Please enter 1, 2, or 3.")
        exit(0)
