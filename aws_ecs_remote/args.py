import argparse


def aws_args(parser: argparse.ArgumentParser,
             profile=""):
    parser.add_argument('--profile', default=profile,
                        help='AWS profile (default: {})'.format(profile))


def aws_ecs_args(parser: argparse.ArgumentParser,
                 cluster='ecs-cluster', bucket='ecs-bucket'):
    parser.add_argument('--ecs-run', action='store_true')
    parser.add_argument('--ecs-cluster', default=cluster,
                        help='AWS ECS cluster (default: {})'.format(cluster))
    parser.add_argument('--ecs-bucket', default=bucket,
                        help='AWS ECS bucket (default: {})'.format(bucket))
