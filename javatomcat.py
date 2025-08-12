import boto3
import subprocess
import csv
from prettytable import PrettyTable
from datetime import datetime

# AWS EC2 client
ec2 = boto3.client('ec2')

# Get list of EC2 instances
def list_instances():
    instances = []
    response = ec2.describe_instances()
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            name = ""
            for tag in instance.get('Tags', []):
                if tag['Key'] == 'Name':
                    name = tag['Value']
            instances.append({
                'InstanceId': instance['InstanceId'],
                'Name': name if name else "No Name",
                'State': instance['State']['Name'],
                'PrivateIp': instance.get('PrivateIpAddress', 'N/A'),
                'PublicIp': instance.get('PublicIpAddress', 'N/A')
            })
    return instances

# Let user choose instance by index
def choose_instance(instances):
    print("\nAvailable Instances:")
    for idx, inst in enumerate(instances):
        print(f"[{idx}] {inst['Name']} ({inst['InstanceId']}) - State: {inst['State']} - Public IP: {inst['PublicIp']}")
    choice = int(input("\nSelect instance index: "))
    return instances[choice]

# Fetch users and apache-tomcat directories
def fetch_details(instance):
    public_ip = instance['PublicIp']
    if public_ip == 'N/A':
        print("No public IP. Cannot SSH.")
        return []

    # Command to list home dirs and apache dirs
    bash_command = r"""
    for user in $(ls /home); do
        dirs=$(find /home/$user -maxdepth 1 -type d \( -name "apache-tomcat*" -o -name "apache*" \) -printf "%f\n" 2>/dev/null)
        if [ -n "$dirs" ]; then
            echo "$user,$dirs"
        fi
    done
    """

    # Run command via SSH
    ssh_cmd = ["ssh", "-o", "StrictHostKeyChecking=no", f"ubuntu@{public_ip}", bash_command]
    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=30)
        if result.stdout.strip():
            rows = []
            for line in result.stdout.strip().split("\n"):
                user, dirs = line.split(",", 1)
                rows.append([instance['Name'], user, dirs])
            return rows
        else:
            return []
    except Exception as e:
        print(f"Error: {e}")
        return []

# Save CSV and print table
def save_and_print(data):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"tomcat_directories_{timestamp}.csv"
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Instance Name", "User", "Tomcat Directories"])
        writer.writerows(data)
    print(f"\nSaved results to {filename}")

    table = PrettyTable(["Instance Name", "User", "Tomcat Directories"])
    for row in data:
        table.add_row(row)
    print("\n" + table.get_string())

if __name__ == "__main__":
    instances = list_instances()
    if not instances:
        print("No instances found.")
    else:
        selected_instance = choose_instance(instances)
        details = fetch_details(selected_instance)
        if details:
            save_and_print(details)
        else:
            print("No apache-tomcat directories found.")
