#!/usr/bin/env python3
import boto3
import csv
import time
from tabulate import tabulate

# Initialize AWS clients
ssm_client = boto3.client("ssm")
ec2_client = boto3.client("ec2")

def list_instances():
    """List running EC2 instances with SSM access."""
    response = ec2_client.describe_instances(
        Filters=[
            {"Name": "instance-state-name", "Values": ["running"]}
        ]
    )
    instances = []
    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:
            instance_id = instance["InstanceId"]
            name_tag = next(
                (tag["Value"] for tag in instance.get("Tags", []) if tag["Key"] == "Name"),
                "NoName"
            )
            instances.append({"id": instance_id, "name": name_tag})
    return instances

def choose_instance(instances):
    """Prompt user to choose an instance."""
    print("\nAvailable Instances:")
    for idx, inst in enumerate(instances, 1):
        print(f"{idx}. {inst['name']} ({inst['id']})")
    choice = int(input("\nSelect an instance number: ")) - 1
    return instances[choice]

def fetch_tomcat_info(instance_id):
    """Fetch Tomcat details using SSM without modifying the instance."""
    command = r"""
ps -ef | grep [t]omcat | awk '{print $1, $8}' | while read user proc; do
    port=$(netstat -tulnp 2>/dev/null | grep java | awk '{print $4}' | awk -F: '{print $NF}' | sort -u | tr '\n' ',')
    tomcat_dir=$(dirname $(readlink -f $(which $proc)) 2>/dev/null || echo "Unknown")
    domain=$(curl -s http://169.254.169.254/latest/meta-data/public-hostname || echo "Unknown")
    echo "$user,$port,$tomcat_dir,$domain"
done
"""
    response = ssm_client.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": [command]},
    )
    command_id = response["Command"]["CommandId"]

    # Wait for command to finish
    time.sleep(2)
    output = ssm_client.get_command_invocation(
        CommandId=command_id, InstanceId=instance_id
    )

    if output["Status"] != "Success":
        return []

    results = []
    for line in output["StandardOutputContent"].strip().split("\n"):
        if line and "," in line:
            user, port, tomcat_dir, domain = line.split(",", 3)
            results.append({
                "Instance ID": instance_id,
                "Port": port,
                "User": user,
                "Tomcat Directory": tomcat_dir,
                "Domain": domain
            })
    return results

def save_csv(results, instance_name):
    """Save results to CSV file."""
    filename = f"tomcat_audit_{instance_name}.csv"
    with open(filename, mode="w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    return filename

def main():
    while True:
        instances = list_instances()
        if not instances:
            print("No running instances found.")
            return

        chosen = choose_instance(instances)
        results = fetch_tomcat_info(chosen["id"])

        if results:
            # Display table
            print("\nTomcat Audit Results:")
            print(tabulate(results, headers="keys", tablefmt="grid"))

            # Save CSV
            csv_file = save_csv(results, chosen["name"])
            print(f"\nResults saved to {csv_file}")
        else:
            print("No Tomcat processes found on this instance.")

        again = input("\nDo you want to check another instance? (y/n): ").strip().lower()
        if again != "y":
            break

if __name__ == "__main__":
    main()
