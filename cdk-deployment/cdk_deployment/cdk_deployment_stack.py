from aws_cdk import (
    App, Stack, Duration, RemovalPolicy,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_s3_notifications as s3n,
    aws_dynamodb as dynamodb,
    aws_apigateway as apigw,
    aws_iam as iam,
)
import aws_cdk as cdk
from constructs import Construct

class CdkDeploymentStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # S3 Bucket for uploaded images
        uploaded_bucket = s3.Bucket(
            self, "UploadedImagesBucket",
            bucket_name="uploaded-images-bucket-20250910",
            removal_policy=RemovalPolicy.DESTROY,  # dev only
            auto_delete_objects=True
        )

        # S3 Bucket for processed images
        processed_bucket = s3.Bucket(
            self, "ProcessedImagesBucket",
            bucket_name="processed-images-bucket-20250910",
            removal_policy=RemovalPolicy.DESTROY,  # dev only
            auto_delete_objects=True
        )

        # DynamoDB Table for image metadata
        image_metadata_table = dynamodb.Table(
            self, "ImageMetadataTable",
            partition_key=dynamodb.Attribute(
                name="image_key",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            removal_policy=RemovalPolicy.DESTROY, # dev only
        )

        # Lambda function to process images
        lambda_fn = _lambda.Function(
            self, "ImageProcessorLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="lambda_function.handler",
            code=_lambda.Code.from_docker_build(path="lambda"),  # folder with lambda_function.py and Dockerfile
            environment={
                "PROCESSED_BUCKET": processed_bucket.bucket_name,
                "METADATA_TABLE": image_metadata_table.table_name,
            },
            memory_size=1024,
            timeout=Duration.seconds(30),
        )

        # Grant permissions
        uploaded_bucket.grant_read(lambda_fn)
        processed_bucket.grant_write(lambda_fn)
        image_metadata_table.grant_read_write_data(lambda_fn) # Grant Lambda write access to DynamoDB table

        # Trigger Lambda on object creation in uploaded bucket
        uploaded_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(lambda_fn)
        )

        # API Gateway for image uploads
        api = apigw.RestApi(
            self, "ImageUploadApi",
            rest_api_name="Image Upload Service",
            description="This service handles image uploads to S3.",
            binary_media_types=["*/*"]
        )

        # IAM Role for API Gateway to write to S3
        api_gateway_s3_role = iam.Role(
            self, "ApiGatewayS3Role",
            assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com"),
            inline_policies={
                "s3-put-object": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["s3:PutObject"],
                            resources=[uploaded_bucket.arn_for_objects("*")]
                        )
                    ]
                )
            }
        )

        # Create a resource for image uploads
        upload_resource = api.root.add_resource("upload")
        object_resource = upload_resource.add_resource("{object}")

        # Add a PUT method to the /upload/{object} resource
        object_resource.add_method(
            "PUT",
            apigw.AwsIntegration(
                service="s3",
                integration_http_method="PUT",
                path=f"{uploaded_bucket.bucket_name}/{{object}}",
                options=apigw.IntegrationOptions(
                    credentials_role=api_gateway_s3_role,
                    request_parameters={
                        "integration.request.path.object": "method.request.path.object",
                        "integration.request.header.Content-Type": "method.request.header.Content-Type"
                    },
                    integration_responses=[
                        apigw.IntegrationResponse(
                            status_code="200",
                            response_parameters={
                                "method.response.header.Content-Type": "integration.response.header.Content-Type"
                            }
                        )
                    ],
                    passthrough_behavior=apigw.PassthroughBehavior.WHEN_NO_MATCH,
                )
            ),
            method_responses=[
                apigw.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Content-Type": True
                    }
                )
            ],
            request_parameters={
                "method.request.path.object": True,
                "method.request.header.Content-Type": True
            },
            authorization_type=apigw.AuthorizationType.IAM
        )

        # Output the API Gateway endpoint URL
        cdk.CfnOutput(
            self, "ApiGatewayUrl",
            value=api.url_for_path("/upload/{object}"),
            description="API Gateway endpoint for image uploads"
        )
