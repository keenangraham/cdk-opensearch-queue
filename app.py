from aws_cdk import App
from aws_cdk import Stack
from aws_cdk import RemovalPolicy

from constructs import Construct

from shared_infrastructure.cherry_lab.environments import US_WEST_2
from shared_infrastructure.cherry_lab.vpcs import VPCs

from aws_cdk.aws_opensearchservice import Domain
from aws_cdk.aws_opensearchservice import EngineVersion
from aws_cdk.aws_opensearchservice import CapacityConfig
from aws_cdk.aws_opensearchservice import EbsOptions
from aws_cdk.aws_opensearchservice import LoggingOptions

from aws_cdk.aws_ec2 import SubnetSelection
from aws_cdk.aws_ec2 import SubnetType


class Opensearch(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        vpcs = VPCs(
            self,
            'VPCs'
        )

        domain = Domain(
            self,
            'Domain',
            version=EngineVersion.OPENSEARCH_1_2,
            capacity=CapacityConfig(
                data_node_instance_type='t3.small.search',
                data_nodes=1,
            ),
            ebs=EbsOptions(
                volume_size=10,
            ),
            logging=LoggingOptions(
                app_log_enabled=True,
                slow_index_log_enabled=True,
                slow_search_log_enabled=True,
            ),
            removal_policy=RemovalPolicy.DESTROY,
            vpc=vpcs.default_vpc,
            vpc_subnets=[
                SubnetSelection(
                    availability_zones=['us-west-2a'],
                    subnet_type=SubnetType.PUBLIC,
                ),
            ],
            advanced_options={
                'indices.query.bool.max_clause_count': '8096'
            }
        )

        domain.app_log_group.apply_removal_policy(
            RemovalPolicy.DESTROY
        )
        domain.slow_index_log_group.apply_removal_policy(
            RemovalPolicy.DESTROY
        )
        domain.slow_search_log_group.apply_removal_policy(
            RemovalPolicy.DESTROY
        )



app = App()


Opensearch(
    app,
    'OpensearchStack',
    env=US_WEST_2,
)


# 'r5.xlarge'

app.synth()
