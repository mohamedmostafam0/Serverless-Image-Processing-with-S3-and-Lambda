from aws_cdk import (
    App, Stack, Duration,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_s3_notifications as s3n,
    aws_dynamodb as dynamodb,
)
from constructs import Construct

class ImageProcessingStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # S3 Bucket for uploaded images
        uploaded_bucket = s3.Bucket(
            self, "UploadedImagesBucket",
            bucket_name="uploaded-images-bucket",
            removal_policy=s3.RemovalPolicy.DESTROY,  # dev only
            auto_delete_objects=True
        )

        # S3 Bucket for processed images
        processed_bucket = s3.Bucket(
            self, "ProcessedImagesBucket",
            bucket_name="processed-images-bucket",
            removal_policy=s3.RemovalPolicy.DESTROY,  # dev only
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
            removal_policy=cdk.RemovalPolicy.DESTROY, # dev only
        )

        # Lambda function to process images
        lambda_fn = _lambda.Function(
            self, "ImageProcessorLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="lambda_function.handler",
            code=_lambda.Code.from_asset("lambda"),  # folder with lambda_function.py
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
