import boto3
from rich.tree import Tree
from rich import print

ecs = boto3.client('ecs')
ec2 = boto3.client('ec2')


def list_clusters():
    return ecs.list_clusters()['clusterArns']


def list_container_instances(cluster):
    return ecs.list_container_instances(cluster=cluster).get('containerInstanceArns', [])


def describe_container_instances(cluster, arns):
    if not arns:
        return []
    return ecs.describe_container_instances(cluster=cluster, containerInstances=arns)['containerInstances']


def list_tasks(cluster, container_instance_arn):
    return ecs.list_tasks(cluster=cluster, containerInstance=container_instance_arn).get('taskArns', [])


def describe_tasks(cluster, arns):
    if not arns:
        return []
    return ecs.describe_tasks(cluster=cluster, tasks=arns)['tasks']


def get_task_def(task_def_arn):
    return ecs.describe_task_definition(taskDefinition=task_def_arn)['taskDefinition']


def main():
    root_tree = Tree("[bold blue]ECS Cluster Overview[/]")

    for cluster_arn in list_clusters():
        cluster_name = cluster_arn.split("/")[-1]
        cluster_tree = root_tree.add(f"[green]Cluster: {cluster_name}[/]")

        container_instance_arns = list_container_instances(cluster_arn)
        container_instances = describe_container_instances(cluster_arn, container_instance_arns)

        for ci in container_instances:
            ci_id = ci['containerInstanceArn'].split("/")[-1]
            ec2_id = ci.get('ec2InstanceId', 'Unknown')
            ci_tree = cluster_tree.add(f"[cyan]Container Instance: {ci_id}[/] (EC2: {ec2_id})")

            task_arns = list_tasks(cluster_arn, ci['containerInstanceArn'])
            tasks = describe_tasks(cluster_arn, task_arns)

            for task in tasks:
                task_id = task['taskArn'].split('/')[-1]
                status = task.get('lastStatus', 'N/A')
                task_def_arn = task['taskDefinitionArn']
                task_tree = ci_tree.add(f"Task: {task_id} (Status: {status})")

                task_def = get_task_def(task_def_arn)
                def_name = task_def['family']
                def_rev = task_def['revision']
                task_tree.add(f"[yellow]Task Definition:[/] {def_name}:{def_rev}")

                for container in task_def.get('containerDefinitions', []):
                    cname = container['name']
                    image = container['image']
                    ports = [str(p['containerPort']) for p in container.get('portMappings', [])]
                    port_str = ", ".join(ports) if ports else "None"
                    container_tree = task_tree.add(f"Container: {cname}")
                    container_tree.add(f"Image: {image}")
                    container_tree.add(f"Ports: {port_str}")

    print(root_tree)


if __name__ == "__main__":
    main()
