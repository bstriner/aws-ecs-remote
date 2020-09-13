import os

import boto3
import glob
import io
import zipfile

def create_bucket(s3, bucket, region=None):
    print("create bucket {} in {}".format(bucket, region))
    if (not region) or region == 'us-east-1':
        kwargs = {}
    else:
        kwargs = {
            'CreateBucketConfiguration': {
                'LocationConstraint': region
            }
        }
    s3.create_bucket(
        ACL='private',
        Bucket=bucket,
        **kwargs)
    """,
    GrantFullControl='string',
    GrantRead='string',
    GrantReadACP='string',
    GrantWrite='string',
    GrantWriteACP='string'
)"""


def ensure_bucket(s3, bucket, region):
    exists = False
    try:
        s3.head_bucket(Bucket=bucket)
        exists = True
    except:
        pass
    if exists:
        print("Bucket exists")
    else:
        print("Create bucket")
        create_bucket(s3=s3, bucket=bucket, region=region)


def upload_as_zip(s3, path, bucket, key):
    stream = io.BytesIO()
    with zipfile.ZipFile(file=stream, mode="w") as z:
        for f in glob.glob(os.path.join(path, "**", "*"), recursive=True):
            if os.path.isfile(f):
                print(f)
                print(f[len(path)+1:])
                z.write(f, f[len(path)+1:])
    stream.seek(0)
    s3.upload_fileobj(Bucket=bucket, Key=key, Fileobj=stream)
