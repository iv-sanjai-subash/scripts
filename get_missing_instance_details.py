import boto3

ec2 = boto3.client('ec2')

with open("missing_instances.txt", "r") as f:
    instance_ids = [line.strip() for line in f if line.strip()]

print(f"🔍 Found {len(instance_ids)} instances in missing_instances.txt")

# Fetch instance details
response = ec2.describe_instances(InstanceIds=instance_ids)

print("\n📋 Instance Details:")
print(f"{'InstanceId':<20} {'State':<10} {'Platform':<10}")

for reservation in response['Reservations']:
    for instance in reservation['Instances']:
        instance_id = instance['InstanceId']
        state = instance['State']['Name']
        # 'Platform' is only present for Windows, otherwise it's Linux
        platform = instance.get('Platform', 'linux')
        print(f"{instance_id:<20} {state:<10} {platform:<10}")
