import boto3
import os
import io
from PIL import Image
import datetime
import logging

# Added a comment to force redeployment

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

processed_bucket = os.environ["PROCESSED_BUCKET"]
metadata_table_name = os.environ["METADATA_TABLE"]
metadata_table = dynamodb.Table(metadata_table_name)

def handler(event, context):
    for record in event["Records"]:
        src_bucket = record["s3"]["bucket"]["name"]
        src_key = record["s3"]["object"]["key"]
        original_file_size = record["s3"]["object"]["size"]

        logger.info(f"Processing image: {src_key} from bucket: {src_bucket}")

        try:
            # Download original image into memory
            in_mem_file = io.BytesIO()
            s3.download_fileobj(src_bucket, src_key, in_mem_file)
            logger.info(f"Successfully downloaded {src_key}")
            in_mem_file.seek(0)

            

            # Open and process image from memory
            with Image.open(in_mem_file) as img:
                original_width, original_height = img.size
                # Dummy processing: resize and compress
                img = img.resize((img.width // 2, img.height // 2))
                processed_width, processed_height = img.size
                
                # Save processed image to an in-memory buffer
                out_mem_file = io.BytesIO()
                img.save(out_mem_file, "JPEG", optimize=True, quality=70)
                out_mem_file.seek(0)
            logger.info(f"Successfully processed {src_key}")

            # Get processed file size
            processed_file_size = out_mem_file.getbuffer().nbytes

            # Upload processed image from memory to target bucket
            dest_key = f"processed-{os.path.basename(src_key)}"
            s3.upload_fileobj(out_mem_file, processed_bucket, dest_key)
            logger.info(f"Successfully uploaded processed image {dest_key} to {processed_bucket}")

            # Store metadata in DynamoDB
            timestamp = datetime.datetime.now().isoformat()
            metadata_table.put_item(
                Item={
                    "image_key": src_key,
                    "original_bucket": src_bucket,
                    "original_key": src_key,
                    "processed_bucket": processed_bucket,
                    "processed_key": dest_key,
                    "timestamp": timestamp,
                    "original_size_bytes": original_file_size,
                    "processed_size_bytes": processed_file_size,
                    "original_dimensions": f"{original_width}x{original_height}",
                    "processed_dimensions": f"{processed_width}x{processed_height}",
                }
            )
            logger.info(f"Successfully stored metadata for {src_key} in DynamoDB.")

        except Exception as e:
            logger.critical(f"Unhandled error processing record for {src_key}: {e}")

    return {
        'statusCode': 200,
        'body': 'Image processing complete'
    }