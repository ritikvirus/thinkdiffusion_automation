# ec2_setup.py

import boto3
import paramiko
import time
import os

def create_ec2_instance():
    ec2 = boto3.resource('ec2', region_name=os.environ['AWS_REGION'])
    instances = ec2.create_instances(
        ImageId='ami-0862be96e41dcbf74',  # Update with the desired AMI ID
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.micro',  # Update with the desired instance type
        KeyName='github_action',  # Update with your key pair name
        TagSpecifications=[{'ResourceType': 'instance', 'Tags': [{'Key': 'Name', 'Value': 'GitHubActionsInstance'}]}]
    )

    instance_id = instances[0].id
    instances[0].wait_until_running()
    print(f'Created instance with ID: {instance_id}')
    return instance_id

def install_nginx(instance_id):
    ec2 = boto3.resource('ec2', region_name=os.environ['AWS_REGION'])
    instance = ec2.Instance(instance_id)
    instance.wait_until_running()
    instance.load()
    public_dns = instance.public_dns_name
    print(f'Instance Public DNS: {public_dns}')

    key_file = 'github_action.pem'  # Update with the path to your private key file
    key = paramiko.RSAKey.from_private_key_file(key_file)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Wait for a while to make sure SSH service is up and running
    time.sleep(60)

    client.connect(hostname=public_dns, username='ubuntu', pkey=key)

    commands = [
        'sudo apt-get update',
        'sudo apt-get install nginx -y'
    ]

    for command in commands:
        stdin, stdout, stderr = client.exec_command(command)
        print(stdout.read().decode())
        print(stderr.read().decode())

    client.close()

if __name__ == "__main__":
    instance_id = create_ec2_instance()
    install_nginx(instance_id)
