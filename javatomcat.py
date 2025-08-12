import boto3
import csv
import re
from datetime import datetime

def list_running_instances():
    ec2 = boto3.client('ec2')
    reservations = ec2.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    instances = []
    for res in reservations['Reservations']:
        for inst in res['Instances']:
            name = next((t['Value'] for t in inst.get('Tags', []) if t['Key'] == 'Name'), 'Unnamed')
            instances.append({
                'id': inst['InstanceId'],
                'name': name,
                'type': inst['InstanceType'],
                'private_ip': inst.get('PrivateIpAddress', 'N/A')
            })
    return instances

def choose_instance(instances):
    print("\nAvailable running instances:")
    for i, inst in enumerate(instances):
        print(f"{i+1}. {inst['name']} ({inst['id']}) - {inst['type']} - {inst['private_ip']}")
    choice = int(input("\nSelect instance number: ")) - 1
    return instances[choice]

def fetch_redirect_ports(instance_id):
    ssm = boto3.client('ssm')
    
    command = (
        "find /home -type f -path '*/apache-tomcat*/conf/server.xml' -exec "
        "grep -H 'redirectPort' {} \\; || echo 'No Tomcat found'"
    )
    
    resp = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": [command]},
    )
    
    cmd_id = resp['Command']['CommandId']
    
    # Wait for output
    while True:
        output = ssm.get_command_invocation(CommandId=cmd_id, InstanceId=instance_id)
        if output['Status'] in ('Success', 'Failed', 'TimedOut', 'Cancelled'):
            break
    
    return output['StandardOutputContent']

def parse_redirect_ports(raw_output):
    results = []
    for line in raw_output.splitlines():
        match = re.search(r"(/.*server\.xml).*redirectPort=\"(\d+)\"", line)
        if match:
            path, port = match.groups()
            username = path.split("/")[2]  # e.g., /home/ubuntu/...
            results.append((username, path, port))
    return results

def save_to_csv(instance_name, results):
    filename = f"tomcat_redirect_ports_{instance_name.replace(' ', '_')}.csv"
    with open(filename, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Username", "Tomcat Path", "RedirectPort"])
        writer.writerows(results)
    return filename

def main():
    instances = list_running_instances()
    if not instances:
        print("No running instances found.")
        return
    
    instance = choose_instance(instances)
    print(f"\nFetching Tomcat redirect ports from {instance['name']} ({instance['id']})...")
    
    raw_output = fetch_redirect_ports(instance['id'])
    
    if "No Tomcat found" in raw_output or not raw_output.strip():
        print("\nNo Tomcat installations with redirectPort found.")
        return
    
    results = parse_redirect_ports(raw_output)
    
    if not results:
        print("\nNo redirectPort entries found.")
        return
    
    print("\n+----------+----------------------------------------------------+--------------+")
    print("| Username | Tomcat Path                                        | RedirectPort |")
    print("+----------+----------------------------------------------------+--------------+")
    for row in results:
        print(f"| {row[0]:<8} | {row[1]:<50} | {row[2]:<12} |")
    print("+----------+----------------------------------------------------+--------------+")
    
    csv_file = save_to_csv(instance['name'], results)
    print(f"\nSaved to: {csv_file}")

if __name__ == "__main__":
    main()
