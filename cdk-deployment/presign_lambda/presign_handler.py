import boto3
import os
import json
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

UPLOAD_BUCKET = os.environ.get("UPLOAD_BUCKET")
PROCESSED_BUCKET = os.environ.get("PROCESSED_BUCKET")
REGION = os.environ.get("AWS_REGION")

s3_client = boto3.client('s3', region_name=REGION)

def handler(event, context):
    # Ensure environment variables are set
    if not UPLOAD_BUCKET or not PROCESSED_BUCKET:
        logger.error("UPLOAD_BUCKET or PROCESSED_BUCKET environment variable not set.")
        return create_response(500, {'error': 'Server configuration error'})

    # Route the request based on the path
    request_path = event.get('path', '')
    if request_path == '/generate-upload-url':
        return handle_generate_upload_url(event)
    elif request_path == '/get-processed-image-url':
        return handle_get_processed_image_url(event)
    else:
        return create_response(404, {'error': 'Not Found'})

def handle_generate_upload_url(event):
    try:
        body = json.loads(event.get('body', '{}'))
        filename = body.get('filename')
        content_type = body.get('contentType')

        if not filename or not content_type:
            return create_response(400, {'error': 'Missing filename or contentType'})

        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': UPLOAD_BUCKET,
                'Key': filename,
                'ContentType': content_type
            },
            ExpiresIn=3600
        )
        return create_response(200, {'url': presigned_url})

    except (json.JSONDecodeError, TypeError):
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except ClientError as e:
        logger.error(f"Error generating upload URL: {e}")
        return create_response(500, {'error': 'Could not generate upload URL'})

def handle_get_processed_image_url(event):
    try:
        params = event.get('queryStringParameters', {})
        filename = params.get('filename')
        if not filename:
            return create_response(400, {'error': 'Missing filename'})

        # Check if the object exists before generating a URL
        s3_client.head_object(Bucket=PROCESSED_BUCKET, Key=filename)

        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': PROCESSED_BUCKET,
                'Key': filename
            },
            ExpiresIn=3600
        )
        return create_response(200, {'url': presigned_url})

    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return create_response(404, {'error': 'File not found'})
        logger.error(f"Error generating get URL: {e}")
        return create_response(500, {'error': 'Could not generate URL'})

def create_response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        },
        'body': json.dumps(body)
    }
