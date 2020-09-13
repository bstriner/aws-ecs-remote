import inspect
import os
import boto3
import uuid

from .bucket import ensure_bucket, upload_as_zip
from datetime import datetime

def run_task(
    cluster,
    bucket=None,
    src=None,
    script=None,
    args=None,
    profile=None,
    base_name=None
):
    session = boto3.Session(profile_name=profile)
    s3 = session.client('s3')
    sts = session.client('sts')
    ecs = session.client('ecs')
    logs = session.client('logs')
    region = session.region_name
    account = sts.get_caller_identity().get('Account')

    if not base_name:
        base_name = "run"
    now = datetime.utcnow()
    nowstr = now.strftime("%Y%m%d-%H%M%S-%f")
    uuid1 = uuid.uuid1()
    name = "{}-{}-{}".format(base_name, nowstr, uuid1)
    if not script:
        script = inspect.stack()[1]
        script = script.filename
        script = os.path.abspath(script)
    if not src:
        src = os.path.abspath(os.path.join(script, '..'))
    if not profile:
        profile = None
    if not bucket:
        bucket = 'aws-ecs-remote-{}-{}'.format(region, account)
        print("no bucket specified. using default bucket {}.".format(bucket))

    print("name: {}".format(name))
    print("script: {}".format(script))
    print("src: {}".format(src))
    print("account: {}".format(account))
    print("region: {}".format(region))
    print("bucket: {}".format(bucket))

    # Ensure bucket exists
    ensure_bucket(s3=s3, bucket=bucket, region=region)

    # Upload src to bucket as a zip
    src_key = "{}/src.zip".format(name)
    src_url = "s3://{}/{}".format(bucket, src_key)
    upload_as_zip(s3=s3, path=src, bucket=bucket, key=src_key)

    # Upload args to bucket as json
    # Ensure cluster exists
    # Ensure task definition exists
    # Run task on ECS

