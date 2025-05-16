import boto3
from datetime import datetime, timedelta

ec2 = boto3.client('ec2')
cloudwatch = boto3.client('cloudwatch')

# Output files
working_file = open("working_instances.txt", "w")
missing_file = open("missing_instances.txt", "w")

def get_all_instance_ids():
    instance_ids = []
    paginator = ec2.get_paginator('describe_instances')
    for page in paginator.paginate():
        for reservation in page['Reservations']:
            for instance in reservation['Instances']:
                instance_ids.append(instance['InstanceId'])
    return instance_ids

def has_recent_datapoints(metric):
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=15)
    response = cloudwatch.get_metric_statistics(
        Namespace=metric['Namespace'],
        MetricName=metric['MetricName'],
        Dimensions=metric['Dimensions'],
        StartTime=start_time,
        EndTime=end_time,
        Period=60,
        Statistics=['Average']
    )
    return len(response['Datapoints']) > 0

def check_instance_metrics(instance_id):
    print(f"\n🔍 Checking memory-related metrics for instance: {instance_id}")
    metrics = cloudwatch.list_metrics(Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}])
    found = False
    for m in metrics['Metrics']:
        name = m['MetricName'].lower()
        if 'mem' in name or 'memory' in name:
            print(f"  📊 Found metric: {m['MetricName']} (Namespace: {m['Namespace']})")
            if has_recent_datapoints(m):
                print("    ✅ Receiving data.")
                return True
            else:
                print("    ❌ No recent data.")
                found = True
    if not found:
        print("  ⚠️ No memory-related metrics found.")
    return False

# Main process
instance_ids = get_all_instance_ids()
print(f"🔎 Total instances found: {len(instance_ids)}")

for instance_id in instance_ids:
    try:
        if check_instance_metrics(instance_id):
            working_file.write(instance_id + "\n")
        else:
            missing_file.write(instance_id + "\n")
    except Exception as e:
        print(f"  ⚠️ Error checking instance {instance_id}: {e}")
        missing_file.write(instance_id + "\n")

working_file.close()
missing_file.close()

print("\n✅ Done! Results saved in 'working_instances.txt' and 'missing_instances.txt'")
