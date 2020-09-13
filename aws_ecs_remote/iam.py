from botocore.exceptions import ClientError
from aws_ecs_remote.boto import is_boto_exception

TASK_ROLE_NAME = 'aws-ecs-remote-task-role'
TASK_ROLE = {
    'description': 'Role for tasks running in containers',
    'policies': ['arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy'],
    'trust': """
{
  "Version": "2008-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
"""
}
INSTANCE_ROLE_NAME = 'aws-ecs-remote-instance-role'
INSTANCE_ROLE = {
    'description': 'Role for instances that start containers',
    'policies': ['arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role'],
    'trust': """
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
"""
}


def get_role(iam, role_name):
    try:
        response = iam.get_role(
            RoleName=role_name
        )
        return response['Role']
    except ClientError as e:
        if is_boto_exception(e, 'NoSuchEntity'):
            return None
        else:
            raise e


def create_role(iam, role_name, description, policies, trust):
    response = iam.create_role(
        # Path='string',
        RoleName=role_name,
        AssumeRolePolicyDocument=trust.strip(),
        Description=description,
        # MaxSessionDuration=123,
        # PermissionsBoundary='string',
        Tags=[
            {
                'Key': 'Source',
                'Value': 'aws-ecs-remote'
            },
        ]
    )
    role = response['Role']
    for policy in policies:
        response = iam.attach_role_policy(
            RoleName=role_name,
            PolicyArn=policy
        )
    return role


def ensure_role(iam, role_name, description, policies, trust):
    role = get_role(iam=iam, role_name=role_name)
    if role is None:
        role = create_role(
            iam=iam,
            role_name=role_name,
            description=description,
            policies=policies,
            trust=trust
        )
    return role

def ensure_task_role(iam, role_name=TASK_ROLE_NAME):
    return ensure_role(iam=iam, role_name=role_name, **TASK_ROLE)
def ensure_instance_role(iam, role_name=INSTANCE_ROLE_NAME):
    return ensure_role(iam=iam, role_name=role_name, **INSTANCE_ROLE)


if __name__ == '__main__':
    import boto3
    session = boto3.Session()
    iam = session.client('iam')
    task_role = ensure_task_role(iam=iam)
    instance_role = ensure_instance_role(iam=iam)
    print("task_role: {}".format(task_role))
    print("instance_role: {}".format(instance_role))
