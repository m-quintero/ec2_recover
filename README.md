# AWS EC2 Root Volume Recovery Tool

## Overview

The AWS EC2 Root Volume Recovery Tool is for quick recovery of AWS EC2 instances by either replacing the root volume using a snapshot or restoring from an AMI backup, mimicking the option available within the console. Basically, scenarios where root volume replacement is necessary, such as recovering from a corrupted root volume or reverting to a previous known good state.

**DISCLAIMER:** This tool is designed with the option for DESTRUCTIVE operations within an AWS account. It should only be used for specific scenarios where resources need to be terminated or replaced. Ensure you have full knowledge of the actions this tool will perform.

See https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/replace-root.html & 
https://docs.aws.amazon.com/cli/latest/reference/ec2/create-replace-root-volume-task.html for more details
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
   python ec2_root_recovery.py
   ```

2. **Follow the prompts:**

   - **Disclaimer:** You will be prompted to agree to a disclaimer. Type `I AGREE` to continue or `EXIT` to terminate the script.
   - **Select Region:** Choose the AWS region where your instance is located.
   - **Choose Operation:** Select whether to replace the root volume using a snapshot or restore from an AMI backup by entering `1` or `2`.

3. **Option 1 - Replace Root Volume Using a Snapshot:** - This option provides for more granular control over specific snapshots of volumes

   - Enter the instance ID.
   - Enter the snapshot ID to use for the replacement.

4. **Option 2 - Restore from AMI Backup:** - Choose if you have an AMI you'd like to recover the root volume from

   - Set whether you want to delete the replaced volume after any operations.
   - Choose whether to restore the root volume to the launch state, to a specific snapshot, or using an AMI.

### Example Session

```bash
$ python ec2_root_recovery.py
#####################################################################
#                           DISCLAIMER                              #
#####################################################################
ATTENTION: You are currently logged into AWS Account ID: 123456789012
WARNING: This tool can perform DESTRUCTIVE operations.
...
Your choice (I AGREE/EXIT): I AGREE
Available regions:
1. us-east-1
2. us-east-2
3. us-west-1
4. us-west-2
5. us-gov-west-1
6. us-gov-east-1
Select a region by entering the corresponding number: 1
Do you want to (1) replace root volume using a snapshot or (2) restore from AMI backup? Enter 1 or 2: 2
Would you like to delete the replaced volume after any operations? Yes or No: NO
Do you want to restore the replacement root volume to the launch state? Yes or No: NO
Do you want to restore the replacement root volume to a specific snapshot? Yes or No: YES
Enter the instance ID: i-0123456789abcdef0
Enter the snapshot ID: snap-0123456789abcdef0
Created replace root volume task with ID: replacevol-0a123456789abcdef0
Waiting for replace root volume task replacevol-0a123456789abcdef0 to complete (current state: pending)
...
```

## Requirements

Make sure that the following packages are listed in your `requirements.txt` file:

```
boto3
colorama
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.


## Author

Michael Quintero (michael.quintero@rackspace.com or michael.quintero@gmail.com)
