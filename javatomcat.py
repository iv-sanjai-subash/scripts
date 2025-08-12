import boto3
import csv
import time
from tabulate import tabulate

# AWS clients
ec2_client = boto3.client('ec2')
ssm_client = boto3.client('ssm')

# Step 1: List all instances
def list_instances():
    instances = []
    reservations = ec2_client.describe_instances()['Reservations']
    for res in reservations:
        for inst in res['Instances']:
            name = ""
            for tag in inst.get('Tags', []):
                if tag['Key'] == 'Name':
                    name = tag['Value']
            instances.append({
                'InstanceId': inst['InstanceId'],
                'Name': name,
                'State': inst['State']['Name']
            })
    return instances

# Step 2: Let user choose an instance
def choose_instance(instances):
    print("\nAvailable Instances:")
    for i, inst in enumerate(instances):
        print(f"{i+1}. {inst['Name']} ({inst['InstanceId']}) - {inst['State']}")
    choice = int(input("\nEnter the number of the instance: ")) - 1
    return instances[choice]['InstanceId'], instances[choice]['Name']

# Step 3: Fetch Tomcat directories
def fetch_tomcat_info(instance_id):
    command = """
    echo "Instance Name: $(hostname)";
    echo "Users:";
    ls /home;
    echo "Tomcat Directories:";
    find /home -type d -name "tomcat*" 2>/dev/null
    """
    response = ssm_client.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={'commands': [command]}
    )
    command_id = response['Command']['CommandId']
    time.sleep(2)
    output = ssm_client.get_command_invocation(
        CommandId=command_id,
        InstanceId=instance_id
    )
    return output['StandardOutputContent']

# Step 4: Parse and save CSV
def save_to_csv(instance_name, instance_id, output):
    users_section = []
    tomcat_dirs = []
    lines = output.strip().split("\n")

    try:
        users_start = lines.index("Users:") + 1
        tomcat_start = lines.index("Tomcat Directories:") + 1
        users_section = lines[users_start:tomcat_start - 1]
        tomcat_dirs = lines[tomcat_start:]
    except ValueError:
        pass

    csv_file = "tomcat_audit.csv"
    with open(csv_file, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Instance Name", "Instance ID", "User", "Tomcat Directory"])
        for user in users_section:
            for tomcat in tomcat_dirs:
                if f"/home/{user}" in tomcat:
                    writer.writerow([instance_name, instance_id, user, tomcat])

    print("\nCSV file saved:", csv_file)
    return csv_file

# Step 5: Print CSV as table
def print_csv_as_table(csv_file):
    with open(csv_file, newline="") as f:
        reader = csv.reader(f)
        data = list(reader)
        print("\nTomcat Audit Results:")
        print(tabulate(data[1:], headers=data[0], tablefmt="grid"))

# Main execution
if __name__ == "__main__":
    instances = list_instances()
    if not instances:
        print("No instances found.")
    else:
        instance_id, instance_name = choose_instance(instances)
        print(f"\nFetching Tomcat info for {instance_name} ({instance_id})...")
        output = fetch_tomcat_info(instance_id)
        csv_file = save_to_csv(instance_name, instance_id, output)
        print_csv_as_table(csv_file)
