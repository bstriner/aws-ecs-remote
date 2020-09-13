from aws_ecs_remote.task_definition import LaunchType, CONTAINER_NAME, describe_task_definition
import itertools
import hashlib
import time
from aws_ecs_remote.cloudwatch import follow_log_events
import warnings


def get_log_paths(containers, container_definitions):
    cdefs = {
        cdef['name']: cdef
        for cdef
        in container_definitions
    }
    ldefs = []
    for container in containers:
        name = container['name']
        cdef = cdefs[name]
        driver = cdef['logConfiguration']['logDriver']
        if driver == 'awslogs':
            log_group = cdef['logConfiguration']['options']['awslogs-group']
            log_prefix = cdef['logConfiguration']['options']['awslogs-stream-prefix']
            taskId = container['taskArn'].split('/')[-1]
            ldefs.append({
                'name': name,
                'group': log_group,
                'prefix': log_prefix,
                'taskId': taskId,
                'stream': '{}/{}/{}'.format(log_prefix, name, taskId)
            })
        else:
            warnings.warn("Container [{}] uses log driver [{}] but should be using [awslogs]".format(
                name, driver
            ))
    return ldefs


def tasks_waiter(ecs, cluster, task_arns, poll_sec=6):
    def waiter():
        done = tasks_stopped(ecs=ecs, cluster=cluster, task_arns=task_arns)
        if not done:
            time.sleep(poll_sec)
        return done
    return waiter


def tasks_stopped(ecs, cluster, task_arns):
    response = ecs.describe_tasks(
        cluster=cluster,
        tasks=task_arns
    )
    tasks = response['tasks']
    for task in tasks:
        if task['lastStatus'] != 'STOPPED':
            return False
    return True


def ecs_run_task(
        ecs, cluster, task_definition, command, subnets, security_groups, launch_type=LaunchType.FARGATE,
        platform_version='1.4.0', container_name=CONTAINER_NAME,
        assign_public_ip='ENABLED',
        started_by='aws-ecs-remote', group='aws-ecs-remote-group'):
    response = ecs.run_task(
        cluster=cluster,
        taskDefinition=task_definition,
        overrides={
            'containerOverrides': [
                {
                    'name': container_name,
                    'command': command
                },
            ]
        },
        count=1,
        startedBy=started_by,
        group=group,
        launchType=launch_type,
        platformVersion=platform_version,
        networkConfiguration={
            'awsvpcConfiguration': {
                'subnets': subnets,
                'securityGroups': security_groups,
                'assignPublicIp': assign_public_ip
            }
        })
    tasks = response['tasks']
    assert len(tasks) == 1
    task = tasks[0]
    return task


if __name__ == "__main__":
    import boto3
    session = boto3.Session()
    ecs = session.client('ecs')
    cluster = 'arn:aws:ecs:us-east-1:683880991063:cluster/columbo-fargate-cluster'
    task = ecs_run_task(
        ecs=ecs,
        cluster=cluster,
        task_definition='fargate-task-definition',
        command=['echo test aws-ecs-remote'],
        subnets=['subnet-0c48b4dd667d2867e'],
        security_groups=['sg-08b550b061776586c'],
        launch_type=LaunchType.FARGATE,
        platform_version='1.4.0',
        assign_public_ip='ENABLED',
        started_by='aws-ecs-remote',
        group='aws-ecs-remote-group')
    task_definition = describe_task_definition(
        ecs=ecs,
        task_definition=task['taskDefinitionArn']
    )
    log_streams = get_log_paths(
        task['containers'], task_definition['containerDefinitions']
    )
    waiter = tasks_waiter(
        ecs=ecs,
        cluster=task['clusterArn'],
        task_arns=[task['taskArn']]
    )
    logs = session.client('logs')
    follow_log_events(
        logs=logs, log_streams=log_streams, waiter=waiter
    )
