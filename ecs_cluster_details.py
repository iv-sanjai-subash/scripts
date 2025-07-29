import boto3
import json

ecs = boto3.client('ecs')
ec2 = boto3.client('ec2')

def list_clusters():
    return ecs.list_clusters()['clusterArns']

def list_container_instances(cluster):
    resp = ecs.list_container_instances(cluster=cluster)
    return resp.get('containerInstanceArns', [])

def describe_container_instances(cluster, instance_arns):
    if not instance_arns:
        return []
    return ecs.describe_container_instances(cluster=cluster, containerInstances=instance_arns)['containerInstances']

def list_tasks(cluster, container_instance_arn):
    return ecs.list_tasks(cluster=cluster, containerInstance=container_instance_arn).get('taskArns', [])

def describe_tasks(cluster, task_arns):
    if not task_arns:
        return []
    return ecs.describe_tasks(cluster=cluster, tasks=task_arns)['tasks']

def get_task_def_details(task_def_arn):
    return ecs.describe_task_definition(taskDefinition=task_def_arn)['taskDefinition']

def get_ec2_instance_ids(container_instances):
    ec2_ids = [ci['ec2InstanceId'] for ci in container_instances if 'ec2InstanceId' in ci]
    return ec2.describe_instances(InstanceIds=ec2_ids)['Reservations'] if ec2_ids else []

def format_output():
    clusters = list_clusters()

    for cluster in clusters:
        print(f"\nCluster: {cluster}")
        container_instance_arns = list_container_instances(cluster)
        container_instances = describe_container_instances(cluster, container_instance_arns)

        for ci in container_instances:
            ec2_id = ci.get('ec2InstanceId', 'Unknown')
            print(f"  ContainerInstance: {ci['containerInstanceArn'].split('/')[-1]}")
            print(f"    EC2 Instance ID: {ec2_id}")

            task_arns = list_tasks(cluster, ci['containerInstanceArn'])
            tasks = describe_tasks(cluster, task_arns)

            for task in tasks:
                task_id = task['taskArn'].split('/')[-1]
                task_def_arn = task['taskDefinitionArn']
                task_status = task.get('lastStatus')
                print(f"    Task: {task_id}")
                print(f"      Task Definition: {task_def_arn.split('/')[-1]}")
                print(f"      Last Status: {task_status}")

                task_def = get_task_def_details(task_def_arn)
                for container_def in task_def.get('containerDefinitions', []):
                    name = container_def.get('name')
                    image = container_def.get('image')
                    ports = [pm['containerPort'] for pm in container_def.get('portMappings', [])]
                    port_list = ', '.join(map(str, ports)) if ports else 'None'
                    print(f"      Container: {name}")
                    print(f"        Image: {image}")
                    print(f"        Ports: {port_list}")

if __name__ == "__main__":
    format_output()
