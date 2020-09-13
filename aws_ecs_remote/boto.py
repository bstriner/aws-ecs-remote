import botocore


def is_boto_exception(e, code):
    return (
        hasattr(e, 'response')
        and 'Error' in e.response
        and 'Code' in e.response['Error']
        and e.response['Error']['Code'] == code
    )
