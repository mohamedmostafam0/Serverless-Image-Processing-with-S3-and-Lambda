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
            auto_delete_objects=True,
            cors=[
                s3.CorsRule(
                    allowed_methods=[s3.HttpMethods.PUT, s3.HttpMethods.POST, s3.HttpMethods.GET, s3.HttpMethods.HEAD],
                    allowed_origins=["*"],
                    allowed_headers=["*"],
                    exposed_headers=["ETag"]
                )
            ]
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

        # --- API Gateway for generating pre-signed URLs ---

        # Lambda function to generate pre-signed URLs
        presign_lambda = _lambda.Function(
            self, "PresignLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="presign_handler.handler",
            code=_lambda.Code.from_asset("presign_lambda"),
            environment={
                "UPLOAD_BUCKET": uploaded_bucket.bucket_name,
                "PROCESSED_BUCKET": processed_bucket.bucket_name,
            }
        )

        # Grant the presign lambda permissions for both buckets
        uploaded_bucket.grant_put(presign_lambda)
        processed_bucket.grant_read(presign_lambda)

        # API Gateway to trigger the presign lambda
        api = apigw.RestApi(
            self, "PresignApi",
            rest_api_name="Image URL Service",
            description="This service generates pre-signed URLs for image uploads and downloads.",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS
            )
        )

        # Add a /generate-upload-url resource and a POST method
        generate_upload_url_resource = api.root.add_resource("generate-upload-url")
        generate_upload_url_resource.add_method(
            "POST",
            apigw.LambdaIntegration(presign_lambda)
        )

        # Add a /get-processed-image-url resource and a GET method
        get_processed_image_url_resource = api.root.add_resource("get-processed-image-url")
        get_processed_image_url_resource.add_method(
            "GET",
            apigw.LambdaIntegration(presign_lambda)
        )

        # Output the API Gateway URL
        cdk.CfnOutput(
            self, "UploadApiUrl",
            value=api.url,
            description="API Gateway endpoint for generating pre-signed upload URLs"
        )
