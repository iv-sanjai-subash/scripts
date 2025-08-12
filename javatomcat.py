import boto3
import time
import json

# AWS clients
ec2 = boto3.client('ec2')
ssm = boto3.client('ssm')

def list_instances():
    """List all running instances with SSM managed status."""
    instances = []
    paginator = ec2.get_paginator('describe_instances')
    for page in paginator.paginate(
        Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
    ):
        for reservation in page['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                name = next(
                    (tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name'),
                    ''
                )
                # Check if SSM managed
                ssm_status = 'No'
                try:
                    ssm_desc = ssm.describe_instance_information(
                        Filters=[{'Key': 'InstanceIds', 'Values': [instance_id]}]
                    )
                    if ssm_desc['InstanceInformationList']:
                        ssm_status = 'Yes'
                except:
                    pass
                instances.append({'id': instance_id, 'name': name, 'ssm': ssm_status})
    return instances

def fetch_redirect_ports(instance_id):
    """Fetch Tomcat redirect ports from the instance using SSM."""
    print(f"\nFetching Tomcat redirect ports from {instance_id}...")
    command = (
        "grep 'redirectPort' /opt/tomcat*/conf/server.xml 2>/dev/null | "
        "sed -n 's/.*redirectPort=\"\\([0-9]\\+\\)\".*/\\1/p' | sort -u"
    )
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": [command]},
    )
    cmd_id = response['Command']['CommandId']

    # Wait for execution to complete
    while True:
        invocation = ssm.get_command_invocation(
            CommandId=cmd_id,
            InstanceId=instance_id
        )
        if invocation['Status'] in ('Success', 'Failed', 'Cancelled', 'TimedOut'):
            break
        time.sleep(2)

    if invocation['Status'] == 'Success':
        output = invocation.get('StandardOutputContent', '').strip()
        if output:
            print(f"\nRedirect ports found:\n{output}\n")
        else:
            print("\nNo redirect ports found.\n")
    else:
        print(f"\nCommand failed with status: {invocation['Status']}\n")

def main():
    while True:
        instances = list_instances()
        ssm_instances = [i for i in instances if i['ssm'] == 'Yes']

        if not ssm_instances:
            print("No SSM-managed running instances found.")
            return

        print("\nAvailable instances:")
        for idx, inst in enumerate(ssm_instances, start=1):
            print(f"{idx}. {inst['name']} ({inst['id']})")

        choice = input("\nSelect instance number (or 'q' to quit): ").strip()
        if choice.lower() == 'q':
            break

        if not choice.isdigit() or int(choice) not in range(1, len(ssm_instances)+1):
            print("Invalid choice. Try again.")
            continue

        instance = ssm_instances[int(choice)-1]
        fetch_redirect_ports(instance['id'])

if __name__ == "__main__":
    main()
