import boto3
import datetime

ec2 = boto3.client('ec2')
cloudwatch = boto3.client('cloudwatch')

# Time range: last 5 minutes
end_time = datetime.datetime.utcnow()
start_time = end_time - datetime.timedelta(minutes=5)

def get_all_instance_ids():
    instance_ids = []
    paginator = ec2.get_paginator('describe_instances')
    for page in paginator.paginate():
        for reservation in page['Reservations']:
            for instance in reservation['Instances']:
                instance_ids.append(instance['InstanceId'])
    return instance_ids

def has_recent_memory_metric(instance_id):
    # List all metrics for this instance
    metrics = cloudwatch.list_metrics(
        Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}]
    ).get('Metrics', [])

    memory_metrics = [m for m in metrics if 'memory' in m['MetricName'].lower()]
    for metric in memory_metrics:
        datapoints = cloudwatch.get_metric_statistics(
            Namespace=metric['Namespace'],
            MetricName=metric['MetricName'],
            Dimensions=metric['Dimensions'],
            StartTime=start_time,
            EndTime=end_time,
            Period=300,
            Statistics=['Average']
        ).get('Datapoints', [])

        if datapoints:
            return True  # Found recent memory metric

    return False  # No recent memory metric found

def main():
    missing_instances = []
    instance_ids = get_all_instance_ids()

    print(f"Checking {len(instance_ids)} instances...\n")

    for instance_id in instance_ids:
        print(f"Checking instance: {instance_id}")
        if not has_recent_memory_metric(instance_id):
            missing_instances.append(instance_id)

    print("\n✅ Instances missing memory metrics in the last 5 minutes:")
    for iid in missing_instances:
        print(iid)

    # Optionally write to file
    with open("missing_memory_metrics.txt", "w") as f:
        for iid in missing_instances:
            f.write(iid + "\n")

if __name__ == "__main__":
    main()
