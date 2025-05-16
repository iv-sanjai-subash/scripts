import boto3

# Your test instance ID
instance_id = 'i-04b414a3d44e09d29'

# Create CloudWatch client
cloudwatch = boto3.client('cloudwatch')

def list_metrics_for_instance(instance_id):
    print(f"Fetching all CloudWatch metrics for instance: {instance_id}\n")

    # List all metrics with the instance ID as a dimension
    paginator = cloudwatch.get_paginator('list_metrics')
    response_iterator = paginator.paginate(
        Dimensions=[
            {'Name': 'InstanceId', 'Value': instance_id}
        ]
    )

    metrics_found = []

    for page in response_iterator:
        for metric in page['Metrics']:
            metric_name = metric['MetricName']
            namespace = metric['Namespace']
            metrics_found.append((namespace, metric_name))

    if metrics_found:
        print(f"✅ Found {len(metrics_found)} metrics:\n")
        for ns, name in sorted(set(metrics_found)):
            print(f"- {name} (Namespace: {ns})")
    else:
        print("❌ No metrics found for this instance.")

if __name__ == "__main__":
    list_metrics_for_instance(instance_id)
