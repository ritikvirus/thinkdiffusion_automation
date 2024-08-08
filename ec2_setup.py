# ec2_setup.py

import boto3
import paramiko
import time
import os
import yaml
import requests
import wget

def create_ec2_instance():
    ec2 = boto3.resource('ec2', region_name=os.environ['AWS_REGION'])
    instances = ec2.create_instances(
        ImageId='ami-0c220b6be555839ef',  # Update with the desired AMI ID
        MinCount=1,
        MaxCount=1,
        InstanceType='g6.xlarge',  # Update with the desired instance type
        KeyName='gitaction',  # Update with your key pair name
        SecurityGroupIds=['sg-022d05b4b6bd78b78'],  # Update with your security group ID
        TagSpecifications=[{'ResourceType': 'instance', 'Tags': [{'Key': 'Name', 'Value': 'GitHubActionsInstance'}]}]
    )

    instance_id = instances[0].id
    instances[0].wait_until_running()
    print(f'Created instance with ID: {instance_id}')
    return instance_id

def wait_for_instance(instance_id):
    ec2 = boto3.resource('ec2', region_name=os.environ['AWS_REGION'])
    instance = ec2.Instance(instance_id)
    instance.wait_until_running()
    instance.load()
    public_dns = instance.public_dns_name
    print(f'Instance Public DNS: {public_dns}')
    return public_dns

def execute_remote_commands(ip, key_file, commands):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    retry_count = 0
    max_retries = 20
    retry_delay = 5  # Retry delay in seconds

    while retry_count < max_retries:
        try:
            print(f"Connecting to {ip} with key {key_file}")
            ssh.connect(ip, username='ubuntu', key_filename=key_file, timeout=5)
            print("Connected")

            for command in commands:
                print(f"Executing command: {command}")
                _, stdout, stderr = ssh.exec_command(command)
                print("Command executed")

                print("stdout:")
                print(stdout.read().decode('utf-8'))

                print("stderr:")
                print(stderr.read().decode('utf-8'))

            ssh.close()
            print("SSH connection closed")
            break
        except Exception as e:
            print(f"Error executing remote commands: {e}")
            print(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            retry_count += 1

    if retry_count >= max_retries:
        print(f"Failed to connect after {max_retries} attempts. Exiting.")

def read_config():
    with open('config.yaml', 'r') as file:
        return yaml.safe_load(file)

def check_and_download_models(models):
    for model_name, url in models.items():
        model_path = f'/home/ubuntu/pre_models/models/checkpoints/{model_name}'
        if not os.path.exists(model_path):
            print(f"Downloading {model_name} from {url}")
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                with open(model_path, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
            else:
                print(f"Failed to download {model_name} from {url}")

if __name__ == "__main__":
    config = read_config()

    instance_id = create_ec2_instance()
    public_dns = wait_for_instance(instance_id)

    commands = [
        'sudo apt-get update'
    ]

    if config.get('comfyui_update'):
        commands.append('cd /home/ubuntu/ComfyUI && git fetch && git pull')

    if config.get('comfyui_requirements_install'):
        commands.append('cd /home/ubuntu/ComfyUI && pip install -r requirements.txt')

    key_file = 'gitaction.pem'  # Update with the path to your private key file
    execute_remote_commands(public_dns, key_file, commands)

    checkpoints_models_list = config.get('checkpoints_models_list', {})
    check_and_download_models(checkpoints_models_list)
