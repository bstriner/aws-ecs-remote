from datetime import datetime
from botocore.exceptions import ClientError
from aws_ecs_remote.boto import is_boto_exception
LOG_FORMAT = '{dt}: {message}'
LOG_LIMIT = 100


def log_event_handler(log_format=LOG_FORMAT):
    def handler(event):
        timestamp = event['timestamp']
        dt = datetime.fromtimestamp(timestamp/1000.)
        dt = dt.isoformat()
        message = event['message']
        print(log_format.format(dt=dt, message=message, timestamp=timestamp))
    return handler


def follow_log_events(logs, log_streams, waiter, log_handler=log_event_handler()):
    tokens = None
    done = False
    while not done:
        tokens = handle_log_events(
            logs=logs,
            log_streams=log_streams,
            tokens=tokens,
            log_handler=log_handler
        )
        done = waiter()
    tokens = handle_log_events(
        logs=logs,
        log_streams=log_streams,
        tokens=tokens,
        log_handler=log_handler
    )


def handle_log_events(logs, log_streams, tokens=None, log_handler=log_event_handler()):
    if tokens is None:
        tokens = [None for _ in log_streams]
    next_tokens = []
    for log_stream, token in zip(log_streams, tokens):
        kwargs = {}
        if token:
            kwargs['nextToken'] = token
        response = None
        try:
            response = logs.get_log_events(
                logGroupName=log_stream['group'],
                logStreamName=log_stream['stream'],
                limit=LOG_LIMIT,
                startFromHead=True,
                **kwargs
            )
        except ClientError as e:
            if is_boto_exception(e, 'ResourceNotFoundException'):
                # no logs
                pass
            else:
                raise e
        if response:
            next_tokens.append(response['nextForwardToken'])
            events = response['events']
            for event in events:
                log_handler(event)
        else:
            next_tokens.append(None)
    return next_tokens


if __name__ == '__main__':
    import boto3
    session = boto3.Session()
    logs = session.client('logs')
    log_streams = [{
        'name': 'container',
        'group': '/ecs/fargate-task-definition',
        'prefix': 'ecs',
        'taskId': '155dc40b-0597-4ece-a31a-27c2d4f1abe4',
        'stream': 'ecs/container/155dc40b-0597-4ece-a31a-27c2d4f1abe4'
    }]

    handle_log_events(
        logs=logs,
        log_streams=log_streams
    )
