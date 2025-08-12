import boto3
import time
import csv
from datetime import datetime

ssm = boto3.client('ssm')
ec2 = boto3.client('ec2')

def list_instances():
    """List running EC2 instances that have SSM agent enabled."""
    instances = []
    paginator = ec2.get_paginator('describe_instances')
    for page in paginator.paginate(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]):
        for reservation in page['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                name = next((t['Value'] for t in instance.get('Tags', []) if t['Key'] == 'Name'), '')
                instances.append({'id': instance_id, 'name': name})
    return instances

def fetch_redirect_ports(instance_id):
    """Run SSM command to fetch Tomcat redirect ports from server.xml."""
    print(f"\nFetching Tomcat redirect ports from {instance_id}...")

    # Command to search for redirectPort in Tomcat config
    command = "grep -R 'redirectPort' /opt/tomcat*/conf/server.xml 2>/dev/null || echo 'No redirectPort found'"

    # Send SSM command
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName='AWS-RunShellScript',
        Parameters={'commands': [command]},
    )

    command_id = response['Command']['CommandId']

    # Poll for status
    while True:
        invocation = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
        status = invocation['Status']
        if status in ['Success', 'Failed', 'Cancelled', 'TimedOut']:
            break
        time.sleep(2)

    # Display output
    output = invocation['StandardOutputContent'].strip()
    if not output:
        output = "No redirectPort found"
    print(f"Redirect Port(s):\n{output}\n")
    return output

def main():
    instances = list_instances()
    if not instances:
        print("No running instances found.")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    csv_file = f"tomcat_redirect_ports_{timestamp}.csv"

    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Instance Name", "Instance ID", "Redirect Ports"])

        for idx, instance in enumerate(instances, 1):
            print(f"[{idx}] {instance['name']} ({instance['id']})")

        while True:
            try:
                choice = int(input("\nSelect an instance number (0 to exit): "))
                if choice == 0:
                    break
                if 1 <= choice <= len(instances):
                    selected = instances[choice - 1]
                    ports = fetch_redirect_ports(selected['id'])
                    writer.writerow([selected['name'], selected['id'], ports])
                else:
                    print("Invalid choice.")
            except ValueError:
                print("Please enter a valid number.")

    print(f"\nReport saved as {csv_file}")

if __name__ == "__main__":
    main()
