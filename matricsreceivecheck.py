import boto3
import datetime

# Instance ID
instance_id = 'i-04b414a3d44e09d29'
metric_name = 'mem_used_percent'
namespace = 'CWAgent'

# Time range: last 5 minutes
end_time = datetime.datetime.utcnow()
start_time = end_time - datetime.timedelta(minutes=5)

cloudwatch = boto3.client('cloudwatch')

def check_memory_metric():
    response = cloudwatch.get_metric_statistics(
        Namespace=namespace,
        MetricName=metric_name,
        Dimensions=[
            {'Name': 'InstanceId', 'Value': instance_id}
        ],
        StartTime=start_time,
        EndTime=end_time,
        Period=60,
        Statistics=['Average']
    )

    datapoints = response['Datapoints']
    if datapoints:
        print(f"✅ Memory metric '{metric_name}' is ACTIVE. Received {len(datapoints)} datapoints in the last 5 minutes.")
        for dp in sorted(datapoints, key=lambda x: x['Timestamp']):
            print(f"  - {dp['Timestamp']} → {dp['Average']:.2f}%")
    else:
        print(f"❌ No datapoints received for memory metric '{metric_name}' in the last 5 minutes.")

if __name__ == "__main__":
    check_memory_metric()
