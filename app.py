from aws_cdk import App
from aws_cdk import Stack
from aws_cdk import RemovalPolicy
from aws_cdk import CfnOutput

from constructs import Construct

from shared_infrastructure.cherry_lab.environments import US_WEST_2
from shared_infrastructure.cherry_lab.vpcs import VPCs

from aws_cdk.aws_opensearchservice import Domain
from aws_cdk.aws_opensearchservice import EngineVersion
from aws_cdk.aws_opensearchservice import CapacityConfig
from aws_cdk.aws_opensearchservice import EbsOptions
from aws_cdk.aws_opensearchservice import LoggingOptions

from aws_cdk.aws_ec2 import Port
from aws_cdk.aws_ec2 import SubnetSelection
from aws_cdk.aws_ec2 import SubnetType

from aws_cdk.aws_ecs import ContainerImage

from aws_cdk.aws_ecs_patterns import QueueProcessingFargateService


class Opensearch(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        vpcs = VPCs(
            self,
            'VPCs'
        )

        self.domain = Domain(
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

        self.domain.app_log_group.apply_removal_policy(
            RemovalPolicy.DESTROY
        )
        self.domain.slow_index_log_group.apply_removal_policy(
            RemovalPolicy.DESTROY
        )
        self.domain.slow_search_log_group.apply_removal_policy(
            RemovalPolicy.DESTROY
        )

        CfnOutput(
            self,
            'DomainEndpoint',
            value=self.domain.domain_endpoint,
        )



class Services(Stack):
    def __init__(self, scope: Construct, construct_id: str, opensearch: Opensearch, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        image = ContainerImage.from_asset(
            './service'
        )
        
        vpcs = VPCs(
            self,
            'VPCs'
        )

        service1 = QueueProcessingFargateService(
            self,
            'QueueProcessingFargateService1',
            image=image,
            assign_public_ip=True,
            min_scaling_capacity=1,
            max_scaling_capacity=1,
            vpc=vpcs.default_vpc,
            enable_execute_command=True,
            environment={
                'OPENSEARCH_URL': opensearch.domain.domain_endpoint,
            }
        )

        service2 = QueueProcessingFargateService(
            self,
            'QueueProcessingFargateService2',
            cluster=service1.cluster,
            image=image,
            assign_public_ip=True,
            min_scaling_capacity=1,
            max_scaling_capacity=1,
            enable_execute_command=True,
            environment={
                'OPENSEARCH_URL': opensearch.domain.domain_endpoint,
            }
        )

        service1.service.connections.allow_to(
            opensearch.domain,
            Port.tcp(443),
            description='Allow connection to Opensearch',
        )

        service2.service.connections.allow_to(
            opensearch.domain,
            Port.tcp(443),
            description='Allow connection to Opensearch',
        )

        opensearch.domain.grant_read_write(
            service1.service.task_definition.task_role
        )
        opensearch.domain.grant_read_write(
            service2.service.task_definition.task_role
        )


app = App()

opensearch = Opensearch(
    app,
    'OpensearchStack',
    env=US_WEST_2,
)

Services(
    app,
    'Services',
    opensearch=opensearch,
    env=US_WEST_2,
)

app.synth()
