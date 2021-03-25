import os
import time
import json
import subprocess
import argparse

AWS = 'aws'   # path to `aws` CLI executable

PERMISSION_FILE_PATH = '~/.ssh/dlad-aws.pem'
AMI = 'ami-05f6982c11ca3027d' # Deep Learning AMI (Ubuntu 18.04) Version 41.0
INSTANCE_TYPE = 'p2.xlarge'
VOLUME_TYPE = 'gp2'
REGION = 'us-east-1'
NON_ROOT = 'ubuntu'
TIMEOUT = 24  # in hours
RSYNC_EXCLUDE = "--exclude 'wandb/' --exclude 'doc/'"
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))


class color:
   GREEN = '\033[32m'
   END = '\033[0m'

def build_ssh_cmd(hostname):
    ssh_options = f"-q -o StrictHostKeyChecking=no -o LogLevel=ERROR -o ConnectTimeout=180 -i {PERMISSION_FILE_PATH}"
    return f'ssh {ssh_options} {NON_ROOT}@{hostname}'

def build_rsync_cmd(hostname):
    ssh_options = f"-q -o StrictHostKeyChecking=no -o LogLevel=ERROR -o ConnectTimeout=180 -i {PERMISSION_FILE_PATH}"
    return f"rsync -av -e 'ssh {ssh_options}' . {RSYNC_EXCLUDE} {NON_ROOT}@{hostname}:~/code/"

def setup_s3_bucket():
    if not os.path.exists("aws_configs/default_s3_bucket.txt"):
        print("You currently have no AWS S3 bucket specified. These are your existing buckets:\n")
        os.system("aws s3 ls")
        print("\nThis list is empty for a new account.")
        print("Choose an existing or new name for your bucket according to the naming rule (https://docs.aws.amazon.com"
              "/awscloudtrail/latest/userguide/cloudtrail-s3-bucket-naming-requirements.html).")
        bucket_name = input("Bucket name (without s3://): ")
        print(f"Create bucket {bucket_name}...")
        if os.system(f"aws s3 mb s3://{bucket_name}") != 0:
            quit()
        if os.system(f'aws s3api put-public-access-block --bucket {bucket_name} --public-access-block-configuration '
                         f'"BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,'
                         f'RestrictPublicBuckets=true"') != 0:
            quit()
        with open("aws_configs/default_s3_bucket.txt", "w") as fh:
            fh.write(bucket_name)

def setup_group_id():
    if not os.path.exists("aws_configs/group_id.txt"):
        group_id = input("Please enter your DLAD group ID as raw number: ")
        try:
            int(group_id)  # test if conversion is valid
        except ValueError:
            print("Your group ID is not a valid integer.")
            quit()
        assert 0 <= int(group_id) < 100, "Your group ID should be between 0 and 100."
        with open("aws_configs/group_id.txt", "w") as fh:
            fh.write(group_id)

def setup_wandb():
    if not os.path.exists("aws_configs/wandb.key"):
        wandb_key = input("Please enter your wandb key (https://wandb.ai/authorize): ")
        with open("aws_configs/wandb.key", "w") as fh:
            fh.write(wandb_key)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="config")
    parser.add_argument(
        "--bare", action="store_true",
        help="Do NOT automatically launch aws_train_in_tmux.sh after initialization.",
    )
    args = parser.parse_args()

    setup_wandb()
    setup_s3_bucket()
    setup_group_id()

    if args.bare:
        print(color.GREEN + "You are launching an instance without training. Have you intended this?" + color.END)
        time.sleep(5)

    print("Launch instance (Ctrl+C won't stop the process anymore)...")

    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    tag = f'{timestamp}'

    instance_tag = 'ResourceType=instance,Tags=[{Key=Name,Value=' + tag + '}]'
    spot_tag = 'ResourceType=spot-instances-request,Tags=[{Key=Name,Value=' + tag + '}]'


    # Refer to https://docs.aws.amazon.com/cli/latest/reference/ec2/run-instances.html
    my_cmd = [AWS, 'ec2', 'run-instances',
              '--tag-specifications', instance_tag,
              '--tag-specifications', spot_tag,
              '--instance-type', INSTANCE_TYPE,
              '--image-id', AMI,
              '--key-name', 'dlad-aws',
              '--security-groups', 'dlad-sg',
              '--iam-instance-profile', 'Name="dlad-instance-profile"',
              '--block-device-mappings', f'DeviceName="/dev/sda1",Ebs={{VolumeType="{VOLUME_TYPE}"}}',
              '--instance-market-options', f'file://{TOOLS_DIR}/aws_configs/spot-options.json'
    ]


    response = None
    successful = False
    while not successful:
        try:
            response = json.loads(subprocess.check_output(my_cmd))
            successful = True
        except subprocess.CalledProcessError:
            wait_seconds = 120
            print(f'launch unsuccessfull, retrying in {wait_seconds} seconds...')
            time.sleep(wait_seconds)


    instance_id = response['Instances'][0]['InstanceId']
    dns_response = json.loads(subprocess.check_output([AWS,
                                                       'ec2',
                                                       'describe-instances',
                                                       '--region',
                                                       REGION,
                                                       '--instance-ids',
                                                       instance_id]))
    instance_dns = dns_response['Reservations'][0]['Instances'][0]['PublicDnsName']
    ssh_command = build_ssh_cmd(instance_dns)

    print('Wait for instance and copy files to AWS...')
    successful = False
    while not successful:
        try:
            rsync_cmd = build_rsync_cmd(instance_dns)
            subprocess.run([rsync_cmd], shell=True, check=True)
            successful = True
        except subprocess.CalledProcessError:
            print(f'File transfer unsuccessfull, retrying...')

    print(f'\nSet timeout to {TIMEOUT} hours.\n')
    subprocess.run([f"{ssh_command} nohup bash /home/ubuntu/code/aws_timeout.sh {TIMEOUT}h > timeout.log 2>&1 &"], shell=True, check=True)

    if not args.bare:
        print('Start training in tmux session...')
        subprocess.run([f"{ssh_command} bash /home/ubuntu/code/aws_train_in_tmux.sh"], shell=True, check=True)

    print(f'Sucessfully started instance {instance_id} with tag {tag}')
    print('Connect to instance using ssh:')
    print(color.GREEN + ssh_command + color.END)
    print('Rsync file updates:')
    print(color.GREEN + rsync_cmd + color.END)
    if not args.bare:
        print('Connect to tmux session using ssh:')
        print(color.GREEN + f"{ssh_command} -t tmux attach-session -t dlad" + color.END)

    with open('aws.log', 'a') as file_name:
        file_name.write(f'{tag}\n')
        file_name.write(f'{ssh_command}\n\n')
