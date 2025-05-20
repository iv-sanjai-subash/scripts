import boto3

# Initialize EC2 client
ec2 = boto3.client('ec2')

# Read instance IDs from file
with open('missing_instances.txt', 'r') as f:
    instance_ids = [line.strip() for line in f if line.strip()]

# Describe instances
response = ec2.describe_instances(InstanceIds=instance_ids)

print("\nInstance Info:\n")
for reservation in response['Reservations']:
    for instance in reservation['Instances']:
        instance_id = instance['InstanceId']
        state = instance['State']['Name']
        platform = instance.get('Platform', 'Linux/Other')  # Windows shows explicitly, others don't
        print(f"- Instance ID: {instance_id}")
        print(f"  Platform: {platform}")
        print(f"  State   : {state}\n")
