import boto3
import csv
import subprocess
from tabulate import tabulate

def list_instances():
    ec2 = boto3.client('ec2')
    instances = []
    reservations = ec2.describe_instances()['Reservations']
    for r in reservations:
        for i in r['Instances']:
            name = ''
            for tag in i.get('Tags', []):
                if tag['Key'] == 'Name':
                    name = tag['Value']
            instances.append({
                'InstanceId': i['InstanceId'],
                'Name': name,
                'State': i['State']['Name']
            })
    return instances

def fetch_tomcat_details(instance_id):
    ssm = boto3.client('ssm')
    command = """
    for userdir in /home/*; do
        if [ -d "$userdir" ]; then
            username=$(basename "$userdir")
            tomcats=$(find "$userdir" -maxdepth 1 -type d \\( -name "apache-tomcat*" -o -name "apache*" \\) 2>/dev/null | xargs -n 1 basename)
            if [ -n "$tomcats" ]; then
                echo "$username|$tomcats"
            fi
        fi
    done
    """
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={'commands': [command]}
    )
    command_id = response['Command']['CommandId']
    output = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
    return output['StandardOutputContent']

def main():
    instances = list_instances()
    print(tabulate(instances, headers="keys"))

    choice = int(input("\nSelect instance index: "))
    instance_id = instances[choice]['InstanceId']
    instance_name = instances[choice]['Name']

    details = fetch_tomcat_details(instance_id)
    rows = []
    for line in details.strip().split("\n"):
        if "|" in line:
            user, dirs = line.split("|", 1)
            rows.append([instance_name, user, dirs])

    # Save to CSV
    with open('tomcat_directories.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Instance Name', 'User', 'Tomcat Directories'])
        writer.writerows(rows)

    print("\nFound Tomcat Directories:")
    print(tabulate(rows, headers=['Instance Name', 'User', 'Tomcat Directories']))

if __name__ == "__main__":
    main()
