import boto3
import time
import csv
from tabulate import tabulate
from datetime import datetime

def list_instances():
    ec2 = boto3.client("ec2")
    response = ec2.describe_instances()
    instances = []
    for reservation in response.get("Reservations", []):
        for instance in reservation.get("Instances", []):
            name = "(no name)"
            for tag in instance.get("Tags", []):
                if tag["Key"] == "Name":
                    name = tag["Value"]
            instances.append({
                "InstanceId": instance["InstanceId"],
                "Name": name,
                "State": instance["State"]["Name"]
            })
    return instances

def send_ssm_command(instance_id, command):
    ssm = boto3.client("ssm")
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": [command]}
    )
    return response["Command"]["CommandId"]

def get_command_output(ssm, instance_id, command_id):
    while True:
        try:
            output = ssm.get_command_invocation(
                CommandId=command_id,
                InstanceId=instance_id
            )
            if output["Status"] in ("Success", "Failed", "Cancelled", "TimedOut"):
                return output
            else:
                time.sleep(2)
        except ssm.exceptions.InvocationDoesNotExist:
            time.sleep(2)

def main():
    instances = list_instances()
    if not instances:
        print("No EC2 instances found.")
        return

    # Show instances with index
    print("\nAvailable Instances:")
    for idx, inst in enumerate(instances):
        print(f"[{idx}] {inst['Name']} ({inst['InstanceId']}) - {inst['State']}")

    choice = int(input("\nSelect instance index: "))
    if choice < 0 or choice >= len(instances):
        print("Invalid choice.")
        return

    instance = instances[choice]
    instance_id = instance["InstanceId"]

    # Bash script to list users and tomcat directories under /home
    bash_script = """
    for user in $(ls /home); do
        tomcat_dirs=$(find /home/$user -maxdepth 1 -type d \\( -iname "apache-tomcat*" -o -iname "apache*" \\) 2>/dev/null | xargs -n 1 basename | paste -sd "," -)
        echo "$user,$tomcat_dirs"
    done
    """

    print(f"\nRunning command on instance {instance['Name']} ({instance_id})...")

    ssm = boto3.client("ssm")
    cmd_id = send_ssm_command(instance_id, bash_script)
    output = get_command_output(ssm, instance_id, cmd_id)

    if output["Status"] != "Success":
        print("Command failed or timed out.")
        print("Error:", output.get("StandardErrorContent", "No error message"))
        return

    # Parse output
    rows = []
    for line in output["StandardOutputContent"].strip().split("\n"):
        if line.strip():
            user, tomcat_dirs = line.split(",", 1)
            if not tomcat_dirs.strip():
                tomcat_dirs = "-"
            rows.append([instance["Name"], user, tomcat_dirs])

    # Save CSV locally
    filename = f"tomcat_directories_{instance['Name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Instance Name", "User", "Tomcat Directories"])
        writer.writerows(rows)

    # Print table
    print("\nTomcat Audit Results:")
    print(tabulate(rows, headers=["Instance Name", "User", "Tomcat Directories"], tablefmt="grid"))
    print(f"\nData saved to: {filename}")

if __name__ == "__main__":
    main()
