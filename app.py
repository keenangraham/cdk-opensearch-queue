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

from aws_cdk.aws_servicediscovery import PrivateDnsNamespace

from aws_cdk.aws_ec2 import Port
from aws_cdk.aws_ec2 import SubnetSelection
from aws_cdk.aws_ec2 import SubnetType

from aws_cdk.aws_ecs import ContainerImage
from aws_cdk.aws_ecs import CloudMapOptions

from aws_cdk.aws_ecs_patterns import ApplicationLoadBalancedFargateService
from aws_cdk.aws_ecs_patterns import ApplicationLoadBalancedTaskImageOptions
from aws_cdk.aws_ecs_patterns import QueueProcessingFargateService

from aws_cdk.aws_iam import PolicyStatement
from aws_cdk.aws_iam import Effect
from aws_cdk.aws_iam import AnyPrincipal


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

        # Access controlled by VPC security groups.
        unsigned_access_policy = PolicyStatement(
            effect=Effect.ALLOW,
            actions=[
                'es:ESHttp*',
            ],
            principals=[
                AnyPrincipal()
            ],
            resources=[
                f'{self.domain.domain_arn}/*'
            ]
        )

        self.domain.add_access_policies(
            unsigned_access_policy
        )

        CfnOutput(
            self,
            'DomainEndpoint',
            value=self.domain.domain_endpoint,
        )



class Services(Stack):
    def __init__(self, scope: Construct, construct_id: str, opensearch: Opensearch, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpcs = VPCs(
            self,
            'VPCs'
        )

        cloud_map_namespace = 'demo.branch-xyz.local'

        api_image = ContainerImage.from_asset(
            './external'
        )

        api = ApplicationLoadBalancedFargateService(
            self,
            'ApplicationLoadBalancedFargateService',
            task_image_options=ApplicationLoadBalancedTaskImageOptions(
                container_name='api',
                image=api_image,
                environment={
                    'OPENSEARCH_URL': opensearch.domain.domain_endpoint,
                    'cloud_map_namespace':  cloud_map_namespace
                }
            ),
            vpc=vpcs.default_vpc,
            enable_execute_command=True,
            assign_public_ip=True,
        )

        api.cluster.add_default_cloud_map_namespace(
            name=cloud_map_namespace
        )

        api.service.enable_cloud_map(
            name='api'
        )

        image = ContainerImage.from_asset(
            './service'
        )

        service1 = QueueProcessingFargateService(
            self,
            'QueueProcessingFargateService1',
            image=image,
            cluster=api.cluster,
            assign_public_ip=True,
            min_scaling_capacity=2,
            max_scaling_capacity=2,
            enable_execute_command=True,
            environment={
                'OPENSEARCH_URL': opensearch.domain.domain_endpoint,
                'cloud_map_namespace':  cloud_map_namespace
            }
        )

        service1.service.enable_cloud_map(
            name='service1'
        )

        service2 = QueueProcessingFargateService(
            self,
            'QueueProcessingFargateService2',
            cluster=api.cluster,
            image=image,
            assign_public_ip=True,
            min_scaling_capacity=3,
            max_scaling_capacity=3,
            enable_execute_command=True,
            environment={
                'OPENSEARCH_URL': opensearch.domain.domain_endpoint,
                'cloud_map_namespace':  cloud_map_namespace,
            }
        )

        service2.service.enable_cloud_map(
            name='service2'
        )

        api.service.connections.allow_to(
            service2.service,
            Port.tcp(8000),
            description='Allow connection to service2',
        )

        api.service.connections.allow_to(
            service1.service,
            Port.tcp(8000),
            description='Allow connection to service1',
        )

        service1.service.connections.allow_to(
            service2.service,
            Port.tcp(8000),
            description='Allow connection to service2',
        )

        service1.service.connections.allow_to(
            api.service,
            Port.tcp(80),
            description='Allow connection to api',
        )

        service1.sqs_queue.grant_send_messages(
            api.task_definition.task_role
        )

        service2.service.connections.allow_to(
            service1.service,
            Port.tcp(8000),
            description='Allow connection to service1',
        )

        service2.service.connections.allow_to(
            api.service,
            Port.tcp(80),
            description='Allow connection to api',
        )

        service2.sqs_queue.grant_send_messages(
            api.task_definition.task_role
        )

        api.service.connections.allow_to(
            opensearch.domain,
            Port.tcp(443),
            description='Allow connection to Opensearch',
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
