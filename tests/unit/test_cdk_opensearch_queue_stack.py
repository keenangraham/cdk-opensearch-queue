import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk_opensearch_queue.cdk_opensearch_queue_stack import CdkOpensearchQueueStack

# example tests. To run these tests, uncomment this file along with the example
# resource in cdk_opensearch_queue/cdk_opensearch_queue_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = CdkOpensearchQueueStack(app, "cdk-opensearch-queue")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
