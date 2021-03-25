## AWS Setup

### Create IAM User

* Sign in to the AWS Management Console and open the IAM console at https://console.aws.amazon.com/iam/.
* In the navigation pane, choose "Users".
* Select "Add User", name the user CLI, and select "Programmatic Access"
* Continue with Permissions and choose "Attach existing policies directly" -> "AmazonEC2FullAccess", "IAMFullAccess",
  and "AmazonS3FullAccess"
* Continue with default settings until you reach the step "Create User"
* To download the key pair, choose Download .csv file. Store the keys in a secure location. You will not have access to 
  the secret access key again after this dialog box closes. Keep the keys confidential.

### Setup AWS CLI

* Install AWS-CLI on your computer using `sudo apt install awscli` or follow 
  https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html
* Configure AWS: Run `aws configure` and provide the IAM credentials, choose us-east-1 as region and json as output format.
* Create ssh key: 
    ```shell script
    mkdir -p ~/.ssh/
    aws ec2 create-key-pair --key-name dlad-aws --query "KeyMaterial" --output text > ~/.ssh/dlad-aws.pem
    chmod 400 ~/.ssh/dlad-aws.pem
    ```
* Create security group:
    ```shell script
    aws ec2 create-security-group --group-name dlad-sg --description "DLAD Security Group"
    aws ec2 authorize-security-group-ingress --group-name dlad-sg --protocol tcp --port 22 --cidr 0.0.0.0/0
    ```
* Create policies, roles, and instance profile to grant permissions to ec2 instances 
  (https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html#launch-instance-with-role).
  This is necessary for aws_stop_self.sh and S3 access from the ec2 instance.
    ```shell script
    cd path/to/this/repositoy
    aws iam create-role --role-name dlad-role --assume-role-policy-document file://aws_configs/ec2-role-trust-policy.json
    aws iam put-role-policy --role-name dlad-role --policy-name EC2-Terminate-Permissions --policy-document file://aws_configs/ec2-terminate-policy.json
    aws iam put-role-policy --role-name dlad-role --policy-name S3-Permissions --policy-document file://aws_configs/s3-access-policy.json 
    aws iam create-instance-profile --instance-profile-name dlad-instance-profile
    aws iam add-role-to-instance-profile --instance-profile-name dlad-instance-profile --role-name dlad-role
    ```
