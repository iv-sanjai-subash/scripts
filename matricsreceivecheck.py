import boto3
import datetime

instance_id = 'i-04b414a3d44e09d29'
namespace = 'CWAgent'

# Metrics to check (you can add more)
memory_metrics = [
    'mem_used_percent',
    'Memory % Committed Bytes In Use',
    'mem_available_percent',
    'MemoryUsed',
    'MemoryAvailable',
]

cloudwatch = boto3.client('cloudwatch')
end_time = datetime.datetime.utcnow()
start_time = end_time - datetime.timedelta(minutes=5)

def check_memory_metrics():
    for metric_name in memory_metrics:
        try:
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
                print(f"✅ Metric: {metric_name} → {len(datapoints)} datapoints")
                for dp in sorted(datapoints, key=lambda x: x['Timestamp']):
                    print(f"  - {dp['Timestamp']} → {dp['Average']:.2f}%")
            else:
                print(f"❌ Metric: {metric_name} → No datapoints in last 5 mins")
        except Exception as e:
            print(f"⚠️  Metric: {metric_name} → Error: {e}")

if __name__ == "__main__":
    check_memory_metrics()
