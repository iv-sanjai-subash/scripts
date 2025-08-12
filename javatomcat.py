import boto3
import csv
import time
from datetime import datetime

# AWS Clients
ec2 = boto3.client('ec2')
ssm = boto3.client('ssm')

# Get list of running EC2 instances
def list_instances():
    instances_info = []
    reservations = ec2.describe_instances(Filters=[
        {'Name': 'instance-state-name', 'Values': ['running']}
    ])['Reservations']

    for r in reservations:
        for i in r['Instances']:
            name = next((t['Value'] for t in i.get('Tags', []) if t['Key'] == 'Name'), 'N/A')
            instances_info.append({
                'id': i['InstanceId'],
                'name': name,
                'type': i['InstanceType'],
                'private_ip': i.get('PrivateIpAddress', 'N/A'),
                'os': detect_os(i)
            })
    return instances_info

# Detect OS from PlatformDetails
def detect_os(instance):
    platform = instance.get('PlatformDetails', '').lower()
    if 'windows' in platform:
        return 'Windows'
    return 'Linux'

# Fetch Tomcat redirect ports via SSM (read-only)
def fetch_redirect_ports(instance_id, os_type):
    if os_type == 'Windows':
        command = 'Select-String -Path "C:\\Program Files\\Apache Software Foundation\\Tomcat*\\conf\\server.xml" -Pattern "redirectPort"'
    else:
        command = "grep -R 'redirectPort' /opt/tomcat*/conf/server.xml || grep -R 'redirectPort' /usr/share/tomcat*/conf/server.xml"

    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName='AWS-RunShellScript' if os_type == 'Linux' else 'AWS-RunPowerShellScript',
        Parameters={'commands': [command]},
    )

    command_id = response['Command']['CommandId']

    # Wait until command completes
    for _ in range(30):
        time.sleep(2)
        try:
            invocation = ssm.get_command_invocation(
                CommandId=command_id,
                InstanceId=instance_id
            )
        except ssm.exceptions.InvocationDoesNotExist:
            continue  # Command not yet registered

        if invocation['Status'] in ['Success', 'Failed', 'Cancelled', 'TimedOut']:
            output = invocation.get('StandardOutputContent', '').strip()
            return parse_redirect_ports(output)

    return ["No ports found"]

# Extract only redirect ports from output
def parse_redirect_ports(output):
    ports = []
    for line in output.splitlines():
        if 'redirectPort' in line:
            import re
            matches = re.findall(r'redirectPort\s*=\s*"(\d+)"', line)
            ports.extend(matches)
    return ports if ports else ["Not Found"]

# Save results to CSV
def save_to_csv(results):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"tomcat_redirect_ports_{timestamp}.csv"
    with open(filename, 'w', newline='') as csvfile:
        fieldnames = ['Instance ID', 'Name', 'Private IP', 'OS', 'Redirect Ports']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(r)
    print(f"\n✅ CSV saved: {filename}")

# Main flow
def main():
    instances = list_instances()
    if not instances:
        print("No running instances found.")
        return

    # Display instances
    print("\nAvailable EC2 Instances:")
    for idx, inst in enumerate(instances, start=1):
        print(f"{idx}. {inst['name']} ({inst['id']}) - {inst['private_ip']} - {inst['os']}")

    while True:
        try:
            choice = int(input("\nSelect an instance number (0 to exit): "))
            if choice == 0:
                break
            if 1 <= choice <= len(instances):
                selected = instances[choice - 1]
                print(f"\nFetching Tomcat redirect ports from {selected['id']}...")
                ports = fetch_redirect_ports(selected['id'], selected['os'])

                print(f"➡ Redirect Ports for {selected['name']} ({selected['id']}): {', '.join(ports)}")

                save_to_csv([{
                    'Instance ID': selected['id'],
                    'Name': selected['name'],
                    'Private IP': selected['private_ip'],
                    'OS': selected['os'],
                    'Redirect Ports': ', '.join(ports)
                }])
            else:
                print("Invalid choice.")
        except ValueError:
            print("Please enter a valid number.")

if __name__ == "__main__":
    main()
