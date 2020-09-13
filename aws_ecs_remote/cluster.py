import warnings

CLUSTER_NAME = 'aws-ecs-remote-cluster'


class FargateProvider:
    FARGATE = 'FARGATE'
    FARGATE_SPOT = 'FARGATE_SPOT'


def get_cluster(ecs, cluster_name=CLUSTER_NAME):
    response = ecs.describe_clusters(
        clusters=[
            cluster_name
        ],
        include=[
            # 'ATTACHMENTS'|'SETTINGS'|'STATISTICS'|'TAGS',
            'SETTINGS', 'TAGS',
        ]
    )
    clusters = response['clusters']
    if len(clusters) > 1:
        warnings.warn('Found {} clusters named [{}]'.format(
            len(clusters),
            cluster_name
        ))
    if len(clusters) > 0:
        return clusters[0]
    else:
        return None


def create_cluster(ecs, cluster_name=CLUSTER_NAME):
    print("Creating cluster [{}]".format(cluster_name))
    response = ecs.create_cluster(
        clusterName=cluster_name,
        tags=[
            {
                'key': 'Source',
                'value': 'aws-ecs-remote'
            },
        ],
        capacityProviders=[
            FargateProvider.FARGATE, FargateProvider.FARGATE_SPOT
        ],
        defaultCapacityProviderStrategy=[
            {
                'capacityProvider': FargateProvider.FARGATE,
                'weight': 1,
                'base': 0
            },
        ]
    )
    cluster = response['cluster']
    return cluster


def ensure_cluster(ecs, cluster_name=CLUSTER_NAME):
    cluster = get_cluster(ecs=ecs, cluster_name=cluster_name)
    if cluster is None:
        cluster = create_cluster(ecs=ecs, cluster_name=cluster_name)
    return cluster


if __name__ == "__main__":
    import boto3
    session = boto3.Session()
    ecs = session.client('ecs')
    cluster = ensure_cluster(ecs)
    print("cluster: {}".format(cluster))
