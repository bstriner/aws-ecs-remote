import warnings
import time
import botocore
SECURITY_GROUP_DESCRIPTION = 'Security group for aws-ecs-remote'
SECURITY_GROUP_NAME = 'aws-ecs-remote-task-security-group'
INTERNET_GATEWAY_NAME = 'aws-ecs-remote-internet-gateway'
SUBNET_NAME = 'aws-ecs-remote-subnet'
VPC_NAME = 'aws-ecs-remote-vpc'
VPC_CIDR = '10.0.0.0/16'
AVAILABLE = 'available'


def ensure_security_group(
        ec2, vpc_id,
        security_group_name=SECURITY_GROUP_NAME,
        description=SECURITY_GROUP_DESCRIPTION):
    security_group = get_security_group(
        ec2=ec2,
        vpc_id=vpc_id,
        security_group_name=security_group_name
    )
    if security_group is None:
        security_group = create_security_group(
            ec2=ec2,
            vpc_id=vpc_id,
            security_group_name=security_group_name,
            description=description
        )
    return security_group


def create_security_group(
        ec2, vpc_id,
        security_group_name=SECURITY_GROUP_NAME,
        description=SECURITY_GROUP_DESCRIPTION):
    try:
        security_group = ec2.create_security_group(
            Description=description,
            GroupName=security_group_name,
            VpcId=vpc_id,
            TagSpecifications=[
                {
                    'ResourceType': 'security-group',
                    'Tags': [
                        {
                            'Key': 'Name',
                            'Value': SECURITY_GROUP_NAME
                        },
                    ]
                },
            ]
        )
    except botocore.exceptions.ClientError as e:
        if (
                hasattr(e, 'response')
                and 'Error' in e.response
                and 'Code' in e.response['Error']
                and e.response['Error']['Code'] == 'InvalidGroup.Duplicate'):
            warnings.warn('Security group vpc=[{vpc_id}] name=[{security_group_name}] already exists.'.format(
                vpc_id=vpc_id, security_group_name=security_group_name
            ))
            security_group = get_security_group(
                ec2=ec2,
                vpc_id=vpc_id,
                security_group_name=security_group_name
            )
            return security_group
        else:
            raise e
    return security_group


def get_security_group(ec2, vpc_id, security_group_name):
    response = ec2.describe_security_groups(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [vpc_id]
            },
            {
                'Name': 'group-name',
                'Values': [security_group_name]
            }
        ]
    )
    sgs = response['SecurityGroups']
    if len(sgs) > 1:
        warnings.warn("Multiple security groups matched vpc=[{vpc_id}] name=[{security_group_name}]".format(
            vpc_id=vpc_id, security_group_name=security_group_name
        ))
    if len(sgs) > 0:
        return sgs[0]
    else:
        return None


def get_vpc(ec2, vpc_name=VPC_NAME, wait=True):
    response = ec2.describe_vpcs(
        Filters=[
            {
                'Name': 'tag:Name',
                'Values': [vpc_name]
            },
        ]
    )
    vpcs = response['Vpcs']
    if len(vpcs) > 1:
        warnings.warn('Multiple VPCs found with name=[{}]'.format(vpc_name))
    if len(vpcs) > 0:
        vpc = vpcs[0]
        if wait:
            vpc = await_vpc(ec2=ec2, vpc=vpc)
        return vpc
    else:
        return None


def get_vpc_by_id(ec2, vpc_id, wait=True):
    response = ec2.describe_vpcs(
        VpcIds=[vpc_id]
    )
    vpcs = response['Vpcs']
    if len(vpcs) > 1:
        warnings.warn('Multiple VPCs found with id=[{}]'.format(vpc_id))
    if len(vpcs) > 0:
        vpc = vpcs[0]
        if wait:
            vpc = await_vpc(ec2=ec2, vpc=vpc)
        return vpc
    else:
        return None


def create_vpc(ec2, region, vpc_name=VPC_NAME, cidr=VPC_CIDR, wait=True):
    response = ec2.create_vpc(
        CidrBlock=cidr,
        AmazonProvidedIpv6CidrBlock=False,
        # Ipv6Pool='string',
        # Ipv6CidrBlock='string',
        # DryRun=True|False,
        InstanceTenancy='default',  # |'dedicated'|'host',
        # Ipv6CidrBlockNetworkBorderGroup='string',
        TagSpecifications=[
            {
                'ResourceType': 'vpc',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': vpc_name
                    }
                ]
            },
        ]
    )
    vpc = response['Vpc']
    vpc_id = vpc['VpcId']
    if wait:
        vpc = await_vpc(ec2=ec2, vpc=vpc)
    ensure_internet_gateway(ec2=ec2, vpc_id=vpc['VpcId'])
    suffix = '.0.0/16'
    if cidr.endswith(suffix):
        subnet_cidr = cidr[:-len(suffix)]+".{}.0/24"
        availability_zones = get_availability_zones(ec2=ec2, region=region)
        for i, az in enumerate(availability_zones):
            create_subnet(
                ec2=ec2,
                vpc_id=vpc_id,
                availability_zone_id=az['ZoneId'],
                cidr=subnet_cidr.format(i)
            )
    else:
        warnings.warn("Cannot automatically create subnets for VPC [{}]. CIDR must end with [{}] but CIDR is [{}]".format(
            vpc_id, suffix, cidr
        ))
    return vpc


def await_vpc(ec2, vpc, poll_sec=6, poll_iter=10):
    vpc_id = vpc['VpcId']
    for _ in range(poll_iter):
        if vpc['State'] == AVAILABLE:
            break
        time.sleep(poll_sec)
        vpc = get_vpc_by_id(
            ec2=ec2,
            vpc_id=vpc_id,
            wait=False
        )
    if vpc['State'] != AVAILABLE:
        warnings.warn('Waited {} seconds, VPC [{}] state is [{}] (expected [{}])'.format(
            poll_sec*poll_iter,
            vpc_id,
            vpc['State'],
            AVAILABLE
        ))
    return vpc


def ensure_vpc(
    ec2, region, vpc_name=VPC_NAME, cidr=VPC_CIDR
):
    vpc = get_vpc(
        ec2=ec2,
        vpc_name=vpc_name
    )
    if vpc is None:
        vpc = create_vpc(
            ec2=ec2,
            vpc_name=vpc_name,
            cidr=cidr,
            region=region
        )
    return vpc


def get_internet_gateway(ec2, vpc_id):
    response = ec2.describe_internet_gateways(
        Filters=[
            {
                'Name': 'attachment.vpc-id',
                'Values': [vpc_id]
            },
        ]
    )
    gateways = response['InternetGateways']
    if len(gateways) > 1:
        warnings.warn('Multiple internet gateways connected to vpc [{}]'.format(
            vpc_id
        ))
    if len(gateways) > 0:
        return gateways[0]
    else:
        return None


def create_internet_gateway(ec2):
    response = ec2.create_internet_gateway(
        TagSpecifications=[
            {
                'ResourceType': 'internet-gateway',
                'Tags': [
                    {
                                'Key': 'Name',
                                'Value': INTERNET_GATEWAY_NAME
                    }
                ]
            }
        ])
    internet_gateway = response['InternetGateway']
    return internet_gateway


def attach_internet_gateway(ec2, vpc_id, internet_gateway_id):
    ec2.attach_internet_gateway(
        InternetGatewayId=internet_gateway_id,
        VpcId=vpc_id
    )


def ensure_internet_gateway(ec2, vpc_id):
    gw = get_internet_gateway(ec2=ec2, vpc_id=vpc_id)
    if gw is None:
        gw = create_internet_gateway(ec2=ec2)
        attach_internet_gateway(
            ec2=ec2,
            vpc_id=vpc_id,
            internet_gateway_id=gw['InternetGatewayId']
        )
    return gw


def get_availability_zones(ec2, region):
    response = ec2.describe_availability_zones(
        Filters=[
            {
                'Name': 'region-name',
                'Values': [region]
            },
        ])
    availability_zones = response['AvailabilityZones']
    return availability_zones


def create_subnet(ec2, vpc_id, availability_zone_id, cidr):
    response = ec2.create_subnet(
        TagSpecifications=[
            {
                'ResourceType': 'subnet',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': SUBNET_NAME
                    },
                ]
            },
        ],
        AvailabilityZoneId=availability_zone_id,
        CidrBlock=cidr,
        VpcId=vpc_id)
    subnet = response['Subnet']
    return subnet


if __name__ == "__main__":
    import boto3
    session = boto3.Session()
    ec2 = session.client('ec2')
    vpc = ensure_vpc(ec2=ec2, region=session.region_name)
    vpc_id = vpc['VpcId']
    sg = ensure_security_group(
        ec2=ec2,
        vpc_id=vpc_id
    )
    print('vpc: {}'.format(vpc))
    print('sg: {}'.format(sg))
