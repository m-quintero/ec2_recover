"""
AWS EC2 Recovery Tool, v1 AUTHOR: michael.quintero@rackspace.com
PURPOSE: To rebuild EC2 instances using the create-replace-root-volume-task action
Additional Info: https://docs.aws.amazon.com/cli/latest/reference/ec2/create-replace-root-volume-task.html
https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/replace-root.html
Usage: python ec2_recover.py, answer the questions, bam!
Note: User is expected to have already set credentials. Requirements are boto3 & colorama
"""

import boto3
import time
from colorama import Fore, Style, init

def get_account_info():
    sts_client = boto3.client('sts')
    try:
        account_id = sts_client.get_caller_identity()["Account"]
        return account_id
    except Exception as e:
        print(f"Error fetching AWS account information: {e}")
        return None

# Used the colorama library to improve readability, but may end up removing to keep the script tight
def print_disclaimer(account_id):
    print(Fore.RED + "#####################################################################")
    print(Fore.RED + "#                           DISCLAIMER                              #")
    print(Fore.RED + "#####################################################################")
    print(f"ATTENTION: You are currently logged into AWS Account ID: {account_id}")
    print("WARNING: This tool can perform DESTRUCTIVE operations.")
    print("It is intended ONLY for use in recovering an AWS account or for specific")
    print("")
    print("By using this tool, YOU ACKNOWLEDGE AND AGREE that:")
    print("")
    print("1. You have full knowledge of the actions this tool will perform.")
    print("2. You've'verified that resources managed by this tool can be modified.")
    print("3. You accept all liability for the use of this tool.")
    print("4. This tool will provide an option to delete the root storage volume")
    print("   This action CANNOT BE UNDONE.")
    print("")
    print("Please type 'I AGREE' to continue or 'EXIT' to terminate.")
    print(Fore.RED + "#####################################################################")
    print(Style.RESET_ALL)

# Add/remove whichever regions you need. I have these as they're my frequently accessed ones
available_regions = [
    'us-east-1',
    'us-east-2',
    'us-west-1',
    'us-west-2',
    'us-gov-west-1',
    'us-gov-east-1'
]

def select_region():
    print("Available regions:")
    for idx, region in enumerate(available_regions):
        print(f"{idx + 1}. {region}")
    
    while True:
        try:
            choice = int(input("Select a region by entering the corresponding number: "))
            if 1 <= choice <= len(available_regions):
                return available_regions[choice - 1]
            else:
                print("Invalid choice. Please enter a number between 1 and", len(available_regions))
        except ValueError:
            print("Invalid input. Please enter a number.")

def wait_for_state(instance_id, state, ec2):
    while True:
        response = ec2.describe_instances(InstanceIds=[instance_id])
        instance_state = response['Reservations'][0]['Instances'][0]['State']['Name']
        if instance_state == state:
            break
        print(f"Waiting for instance {instance_id} to reach state '{state}' (current state: {instance_state})")
        time.sleep(5)

def replace_root_volume(instance_id, snapshot_id, ec2):
    # Create the replace root volume task. Still looking into cloudtrails options for an easy search in regards to the taskid
    print(f"Creating replace root volume task for instance {instance_id} with snapshot {snapshot_id}...")
    response = ec2.create_replace_root_volume_task(
        InstanceId=instance_id,
        SnapshotId=snapshot_id
    )
    task_id = response['ReplaceRootVolumeTask']['ReplaceRootVolumeTaskId']
    print(f"Created replace root volume task with ID: {task_id}")

    # Waiting for the replace root task to complete
    while True:
        task_status = ec2.describe_replace_root_volume_tasks(
            ReplaceRootVolumeTaskIds=[task_id]
        )['ReplaceRootVolumeTasks'][0]['TaskState']
        if task_status in ['completed', 'failed', 'succeeded']:
            break
        print(f"Waiting for replace root volume task {task_id} to complete (current state: {task_status})")
        time.sleep(10)

    if task_status == 'succeeded':
        print(f"Replace root volume task {task_id} completed successfully.")
    elif task_status == 'completed':
        print(f"Replace root volume task {task_id} completed successfully but with warnings.")
    else:
        print(f"Replace root volume task {task_id} failed.")

def restore_from_ami(ami_id, instance_type, key_name, security_group_ids, subnet_id, ec2):
    print(f"Launching new instance from AMI {ami_id}...")
    response = ec2.run_instances(
        ImageId=ami_id,
        InstanceType=instance_type,
        KeyName=key_name,
        SecurityGroupIds=security_group_ids,
        SubnetId=subnet_id,
        MinCount=1,
        MaxCount=1
    )
    new_instance_id = response['Instances'][0]['InstanceId']
    print(f"New instance launched with ID: {new_instance_id}")

    # Gotta wait until the instance state is running
    wait_for_state(new_instance_id, 'running', ec2)
    print(f"New instance {new_instance_id} is now running.")

    return new_instance_id

def perform_replace_root_volume_task(instance_id, snapshot_id=None, ami_id=None, delete_replaced_volume=False, ec2=None):
    params = {
        'InstanceId': instance_id,
        'DeleteReplacedRootVolume': delete_replaced_volume
    }
    if snapshot_id:
        params['SnapshotId'] = snapshot_id
    if ami_id:
        params['ImageId'] = ami_id

    response = ec2.create_replace_root_volume_task(**params)
    task_id = response['ReplaceRootVolumeTask']['ReplaceRootVolumeTaskId']
    print(f"Created replace root volume task with ID: {task_id}")

    # More waiting for tasks to complete, le sigh
    while True:
        task_status = ec2.describe_replace_root_volume_tasks(
            ReplaceRootVolumeTaskIds=[task_id]
        )['ReplaceRootVolumeTasks'][0]['TaskState']
        if task_status in ['completed', 'failed', 'succeeded']:
            break
        print(f"Waiting for replace root volume task {task_id} to complete (current state: {task_status})")
        time.sleep(10)

    if task_status == 'succeeded':
        print(f"Replace root volume task {task_id} completed successfully.")
    elif task_status == 'completed':
        print(f"Replace root volume task {task_id} completed successfully but with warnings.")
    else:
        print(f"Replace root volume task {task_id} failed.")

if __name__ == "__main__":
    # I needed to initialize colorama otherwise, no dice on the red!
    init()  

    account_id = get_account_info()
    if not account_id:
        print("Could not retrieve account information. Exiting.")
        exit(1)

    print_disclaimer(account_id)
    agreement = input("Your choice (I AGREE/EXIT): ")
    if agreement.upper() != "I AGREE":
        print("Exiting tool. No actions have been performed.")
        exit(0)

    region = select_region()
    ec2 = boto3.client('ec2', region_name=region)

    action = input("Do you want to (1) replace root volume using a snapshot or (2) restore from AMI backup? Enter 1 or 2: ")

    # The exit statements were added as the script would contine after selected actions, which was not desired
    if action == '1':
        instance_id = input("Enter the instance ID: ")
        snapshot_id = input("Enter the snapshot ID: ")
        replace_root_volume(instance_id, snapshot_id, ec2)
        exit(0) 

    elif action == '2':
        delete_replaced_volume_answer = input("Would you like to delete the replaced volume after any operations? Yes or No ").strip().lower() == 'yes'
        
        restore_to_launch_state = input("Do you want to restore the replacement root volume to the launch state? Yes or No ").strip().lower() == 'yes'
        if restore_to_launch_state:
            instance_id = input("Enter the instance ID: ")
            perform_replace_root_volume_task(instance_id, delete_replaced_volume=delete_replaced_volume_answer, ec2=ec2)
            exit(0)
        
        restore_to_specific_snapshot = input("Do you want to restore the replacement root volume to a specific snapshot? Yes or No ").strip().lower() == 'yes'
        if restore_to_specific_snapshot:
            instance_id = input("Enter the instance ID: ")
            snapshot_id = input("Enter the snapshot ID: ")
            perform_replace_root_volume_task(instance_id, snapshot_id=snapshot_id, delete_replaced_volume=delete_replaced_volume_answer, ec2=ec2)
            exit(0)

        restore_using_ami = input("Do you want to restore the replacement root volume using an AMI? Yes or No ").strip().lower() == 'yes'
        if restore_using_ami:
            instance_id = input("Enter the instance ID: ")
            ami_id = input("Enter the AMI ID: ")
            perform_replace_root_volume_task(instance_id, ami_id=ami_id, delete_replaced_volume=delete_replaced_volume_answer, ec2=ec2)
            exit(0)

    else:
        print("Invalid option. Please enter 1 or 2.")
        exit(0)
