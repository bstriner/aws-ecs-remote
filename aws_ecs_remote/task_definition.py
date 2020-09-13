import itertools
import hashlib
import time
from botocore.exceptions import ClientError
from aws_ecs_remote.cloudwatch import follow_log_events
import warnings
from aws_ecs_remote.boto import is_boto_exception

CONTAINER_NAME = 'container'
TASK_NAME_FORMAT = 'aws-ecs-remote-task-{launch_type}-{hexdigest}'


class NetworkMode:
    BRIDGE = 'bridge'
    HOST = 'host'
    AWSVPC = 'awsvpc'
    NONE = 'none'


class LogDriver:
    JSON = 'json-file'
    SYSLOG = 'syslog'
    JOURNALD = 'journald'
    GELF = 'gelf'
    FLUENTD = 'fluentd'
    AWSLOGS = 'awslogs'
    SPLUNK = 'splunk'
    AWSFILELENS = 'awsfirelens'


class LaunchType:
    FARGATE = 'FARGATE'
    EC2 = 'EC2'


def describe_task_definition(ecs, task_definition):
    try:
        return ecs.describe_task_definition(
            taskDefinition=task_definition,
            include=[
                'TAGS'
            ]
        )['taskDefinition']
    except ClientError as e:
        if is_boto_exception(e, 'ClientException'):
            # Task definition does not exist
            return None
        else:
            raise e


def make_task_definition_name(launch_type, image, fmt=TASK_NAME_FORMAT):
    hexdigest = hashlib.md5(image.encode('utf-8')).hexdigest()
    return TASK_NAME_FORMAT.format(
        hexdigest=hexdigest,
        launch_type=launch_type
    )


def ensure_task_definition(
        ecs,
        taskRoleArn,
        executionRoleArn,
        image,
        log_region,
        log_prefix='ecs',
        log_group=None,
        definition_name=None,
        networkMode=NetworkMode.AWSVPC,
        launch_type=LaunchType.FARGATE,
        container_name=CONTAINER_NAME):
    if definition_name is None:
        definition_name = make_task_definition_name(
            launch_type=launch_type,
            image=image
        )
    definition = describe_task_definition(
        ecs=ecs, task_definition=definition_name)
    if definition is None:
        definition = create_task_definition(
            ecs=ecs,
            definition_name=definition_name,
            taskRoleArn=taskRoleArn,
            executionRoleArn=executionRoleArn,
            image=image,
            log_region=log_region,
            log_prefix=log_prefix,
            log_group=log_group,
            networkMode=NetworkMode.AWSVPC,
            requiresCompatibilities=LaunchType.FARGATE,
            container_name=CONTAINER_NAME
        )
    return definition


# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.register_task_definition
def create_task_definition(
        ecs,
        definition_name,
        taskRoleArn,
        executionRoleArn,
        image,
        log_region,
        log_prefix='ecs',
        cpu=512,
        memory=2048,
        log_group=None,
        networkMode=NetworkMode.AWSVPC,
        requiresCompatibilities=LaunchType.FARGATE,
        container_name=CONTAINER_NAME):
    print("Registering task definition [{}] for image [{}]".format(
        definition_name,
        image
    ))
    if log_group is None:
        log_group = '/ecs/aws-ecs-remote/{}'.format(definition_name)
    response = ecs.register_task_definition(
        family=definition_name,
        taskRoleArn=taskRoleArn,
        executionRoleArn=executionRoleArn,
        networkMode=networkMode,
        cpu=str(cpu),
        memory=str(memory),
        containerDefinitions=[
            {
                'name': container_name,
                'image': image,
                'essential': True,
                'entryPoint': [
                    'sh', '-c'
                ],
                'command': [
                    'echo Hello World',
                ],
                'disableNetworking': False,
                'privileged': False,
                'readonlyRootFilesystem': False,
                'interactive': False,
                'memory': memory,
                'logConfiguration': {
                    'logDriver': LogDriver.AWSLOGS,
                    'options': {
                        'awslogs-group': log_group,
                        'awslogs-region': log_region,
                        'awslogs-stream-prefix': log_prefix
                    }
                }
            },
        ],
        requiresCompatibilities=[requiresCompatibilities],
        tags=[
            {
                'key': 'aws-ecs-remote-image',
                'value': image
            },
            {
                'key': 'Source',
                'value': 'aws-ecs-remote'
            }
        ]
    )
    return response


if __name__ == "__main__":
    import boto3
    from aws_ecs_remote.iam import ensure_task_role, ensure_instance_role
    session = boto3.Session()
    ecs = session.client('ecs')
    iam = session.client('iam')
    log_region = session.region_name
    task_role = ensure_task_role(iam=iam)
    instance_role = ensure_instance_role(iam=iam)
    task_definition = ensure_task_definition(
        ecs=ecs,
        taskRoleArn=task_role['Arn'],
        executionRoleArn=instance_role['Arn'],
        image='683880991063.dkr.ecr.us-east-1.amazonaws.com/columbo-compute',
        log_region=log_region,
        launch_type=LaunchType.FARGATE)
    print(task_definition)