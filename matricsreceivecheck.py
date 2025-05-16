import boto3
import datetime

# Config
MEMORY_NAMESPACE = 'CWAgent'
MEMORY_METRIC_NAME = 'mem_used_percent'
TIME_RANGE_MINUTES = 15
OUTPUT_FILE_HAS_MEMORY = 'instances_with_memory_metrics.txt'
OUTPUT_FILE_NO_MEMORY = 'instances_without_memory_metrics.txt'

ec2 = boto3.client('ec2')
cloudwatch = boto3.client('cloudwatch')

def list_all_instance_ids():
    instance_ids = []
    paginator = ec2.get_paginator('describe_instances')
    for page in paginator.paginate():
        for reservation in page['Reservations']:
            for instance in reservation['Instances']:
                if instance['State']['Name'] == 'running':
                    instance_ids.append(instance['InstanceId'])
    return instance_ids

def has_memory_metric(instance_id):
    # List metrics for this instance and memory metric name
    response = cloudwatch.list_metrics(
        Namespace=MEMORY_NAMESPACE,
        MetricName=MEMORY_METRIC_NAME,
        Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}]
    )
    return len(response['Metrics']) > 0

def has_memory_data(instance_id):
    end_time = datetime.datetime.utcnow()
    start_time = end_time - datetime.timedelta(minutes=TIME_RANGE_MINUTES)

    response = cloudwatch.get_metric_statistics(
        Namespace=MEMORY_NAMESPACE,
        MetricName=MEMORY_METRIC_NAME,
        Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
        StartTime=start_time,
        EndTime=end_time,
        Period=60,
        Statistics=['Average']
    )
    datapoints = response.get('Datapoints', [])
    return len(datapoints) > 0

def main():
    instance_ids = list_all_instance_ids()
    print(f"Found {len(instance_ids)} running instances")

    with open(OUTPUT_FILE_HAS_MEMORY, 'w') as f_has, open(OUTPUT_FILE_NO_MEMORY, 'w') as f_no:
        for instance_id in instance_ids:
            print(f"Checking instance {instance_id}... ", end="")
            if has_memory_metric(instance_id):
                # Metric exists, check if recent data available
                if has_memory_data(instance_id):
                    print("✅ Memory metric with data")
                    f_has.write(instance_id + '\n')
                else:
                    print("❌ Memory metric but no recent data")
                    f_no.write(instance_id + '\n')
            else:
                print("❌ No memory metric")
                f_no.write(instance_id + '\n')

    print(f"Check complete. Results saved to '{OUTPUT_FILE_HAS_MEMORY}' and '{OUTPUT_FILE_NO_MEMORY}'.")

if __name__ == "__main__":
    main()
