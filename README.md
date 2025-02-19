# AWS EC2 Root Volume Recovery Tool

## Overview

The AWS EC2 Root Volume Recovery Tool provides a streamlined approach for recovering AWS EC2 instances by replacing the root volume using a snapshot or restoring from an AMI backup. Additionally, it now supports batch processing multiple instances in parallel, making large-scale recovery operations more efficient.

This tool is useful in scenarios where root volume replacement is necessary, such as recovering from a corrupted root volume or reverting to a previous known good state.

**DISCLAIMER:** This tool enables DESTRUCTIVE operations within an AWS account. It should only be used for scenarios where resources need to be replaced or restored. Ensure you have full knowledge of the actions this tool will perform.

For additional details, refer to:
- [AWS EC2 Replace Root Volume Documentation](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/replace-root.html)
- [AWS CLI Reference for Replace Root Volume Task](https://docs.aws.amazon.com/cli/latest/reference/ec2/create-replace-root-volume-task.html)

## Prerequisites

- AWS credentials configured on your system.
- Python 3 installed on your system.
- Required Python packages: `boto3` and `colorama`.

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/m-quintero/ec2_recover.git
   cd ec2_recover
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Running the Script

1. **Execute the script:**
   ```bash
   python3 ec2_recover.py
   ```

2. **Follow the prompts:**

   - **Disclaimer:** You will be prompted to agree to a disclaimer. Type `I AGREE` to continue or `EXIT` to terminate the script.
   - **Select AWS Region:** Choose the AWS region where your instance is located.
   - **Choose an Operation:** Select from three recovery options:
     1. **Replace Root Volume Using a Snapshot** – Restore from a specific snapshot.
     2. **Restore from an AMI Backup** – Restore from an AMI.
     3. **Batch Process Recovery** – Process multiple instances in parallel, automatically selecting the latest AMI or snapshot.

### Operation Descriptions

#### **Option 1: Replace Root Volume Using a Snapshot**
- Enter the instance ID.
- Enter the snapshot ID to use for the replacement.

#### **Option 2: Restore from an AMI Backup**
- Enter the instance ID.
- Enter the AMI ID to restore from.

#### **Option 3: Batch Process Recovery**
- Provide a file containing instance IDs (one per line).
- The script will find the most recent AMI or snapshot for each instance and restore accordingly.
- A final summary will display the recovery status of all instances.

### Example Session

```bash
$ python3 ec2_recover.py
#####################################################################
#                           DISCLAIMER                              #
#####################################################################
WARNING: This tool can perform DESTRUCTIVE operations.
By using this tool, YOU ACKNOWLEDGE AND AGREE that:
1. You have full knowledge of the actions this tool will perform.
2. You accept all liability for the use of this tool.
   This action CANNOT BE UNDONE.
#####################################################################

Your choice (I AGREE/EXIT): I AGREE
Enter AWS region: us-east-1
Do you want to (1) replace root volume using a snapshot, (2) restore from AMI backup, or (3) batch process recovery? Enter 1, 2, or 3: 3
Enter the path to the file containing instance IDs: instances
Starting parallel recovery for 3 instances...
Processing recovery for instance: i-0588e50c7676249f2Processing recovery for instance: i-06728a0f22990fe0e

Searching for the most recent AMI for instance i-0588e50c7676249f2...Processing recovery for instance: i-05f6220163f49f67dSearching for the most recent AMI for instance i-06728a0f22990fe0e...

Searching for the most recent AMI for instance i-05f6220163f49f67d...

Using AMI found via instance name pattern for instance i-0588e50c7676249f2: ami-0e686f83c72aaf9b8 (Created: 2025-02-19T20:52:24.000Z)
Using AMI ami-0e686f83c72aaf9b8 for recovery of instance i-0588e50c7676249f2...
Stopping instance i-0588e50c7676249f2...
Using AMI found via instance name pattern for instance i-06728a0f22990fe0e: ami-0798401b4e24423b4 (Created: 2025-02-19T20:52:24.000Z)
Using AMI ami-0798401b4e24423b4 for recovery of instance i-06728a0f22990fe0e...
Stopping instance i-06728a0f22990fe0e...
Using AMI found via instance name pattern for instance i-05f6220163f49f67d: ami-06a6c862833b5b066 (Created: 2025-02-19T20:52:24.000Z)
Using AMI ami-06a6c862833b5b066 for recovery of instance i-05f6220163f49f67d...
Stopping instance i-05f6220163f49f67d...
Instance i-05f6220163f49f67d is now stopped.
Instance i-06728a0f22990fe0e is now stopped.
Detaching old root volume vol-0dbc058b7b7503be4 from i-05f6220163f49f67d...
Detaching old root volume vol-062e305bfb7ebcbda from i-06728a0f22990fe0e...
Creating a new root volume from snapshot snap-06439858dbecc14cd in us-east-1d...
Creating a new root volume from snapshot snap-0836c90c9e1979e5c in us-east-1d...
New root volume created: vol-050185e149320e5cb
New root volume created: vol-0621347ff27d9157a
Instance i-0588e50c7676249f2 is now stopped.
Detaching old root volume vol-0c59f8b9a32c86b23 from i-0588e50c7676249f2...
Creating a new root volume from snapshot snap-03e8c271c87a94ef8 in us-east-1d...
New root volume created: vol-00190ade9673694c2
Attaching new root volume vol-0621347ff27d9157a to instance i-05f6220163f49f67d...
Attaching new root volume vol-050185e149320e5cb to instance i-06728a0f22990fe0e...
Starting instance i-05f6220163f49f67d...
Starting instance i-06728a0f22990fe0e...
Attaching new root volume vol-00190ade9673694c2 to instance i-0588e50c7676249f2...
Starting instance i-0588e50c7676249f2...
Instance i-05f6220163f49f67d has been successfully restored using AMI ami-06a6c862833b5b066!
Instance i-06728a0f22990fe0e has been successfully restored using AMI ami-0798401b4e24423b4!
Instance i-0588e50c7676249f2 has been successfully restored using AMI ami-0e686f83c72aaf9b8!
Batch processing completed.
...
Final instance recovery summary:
Instance i-05f6220163f49f67d: AMI Used - ami-06a6c862833b5b066
Instance i-06728a0f22990fe0e: AMI Used - ami-0798401b4e24423b4
Instance i-0588e50c7676249f2: AMI Used - ami-0e686f83c72aaf9b8

Checking final instance states...
Instance i-0588e50c7676249f2 final state: RUNNING
Instance i-06728a0f22990fe0e final state: RUNNING
Instance i-05f6220163f49f67d final state: RUNNING
```

## Requirements

Ensure that the following packages are listed in your `requirements.txt` file:

```
boto3
colorama
concurrent.futures
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Author

Michael Quintero (michael.quintero@rackspace.com or michael.quintero@gmail.com)

