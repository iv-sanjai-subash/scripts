import boto3
import csv
from tabulate import tabulate
from datetime import datetime

# Initialize AWS clients
ec2 = boto3.client("ec2")
ssm = boto3.client("ssm")

# Step 1: List all instances
instances = ec2.describe_instances()
instance_list = []

for reservation in instances["Reservations"]:
    for instance in reservation["Instances"]:
        instance_id = instance["InstanceId"]
        name = ""
        for tag in instance.get("Tags", []):
            if tag["Key"] == "Name":
                name = tag["Value"]
        state = instance["State"]["Name"]
        instance_list.append({
            "id": instance_id,
            "name": name if name else "(no name)",
            "state": state
        })

# Print instances with index
print("\nAvailable Instances:")
for idx, inst in enumerate(instance_list):
    print(f"{idx}: {inst['name']} ({inst['id']}) - {inst['state']}")

# Select instance
choice = int(input("\nSelect instance index: "))
selected_instance = instance_list[choice]
instance_id = selected_instance["id"]

print(f"\nFetching data from: {selected_instance['name']} ({instance_id})\n")

# Step 2: Run SSM command to fetch users and tomcat dirs
command_script = """
#!/bin/bash
users_list=$(ls -1 /home)
for user in $users_list; do
    tomcat_dirs=$(find /home/$user -maxdepth 1 -type d \\( -name "apache-tomcat*" -o -name "apache*" \\) 2>/dev/null | xargs -n 1 basename)
    echo "$user,$tomcat_dirs"
done
"""

response = ssm.send_command(
    InstanceIds=[instance_id],
    DocumentName="AWS-RunShellScript",
    Parameters={"commands": [command_script]}
)

command_id = response["Command"]["CommandId"]

# Wait for command result
import time
while True:
    output = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
    if output["Status"] in ["Success", "Failed", "Cancelled", "TimedOut"]:
        break
    time.sleep(2)

# Step 3: Process and save output
if output["Status"] == "Success":
    rows = []
    for line in output["StandardOutputContent"].strip().split("\n"):
        if line.strip():
            user, tomcat_dirs = line.split(",", 1)
            rows.append([selected_instance["name"], user, tomcat_dirs if tomcat_dirs else "-"])

    # Save to CSV
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"tomcat_users_{timestamp}.csv"
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Instance Name", "User", "Apache-Tomcat Directories"])
        writer.writerows(rows)

    # Print table
    print(tabulate(rows, headers=["Instance Name", "User", "Apache-Tomcat Directories"], tablefmt="grid"))
    print(f"\nData saved to {filename}")

else:
    print(f"Command failed: {output['StandardErrorContent']}")
