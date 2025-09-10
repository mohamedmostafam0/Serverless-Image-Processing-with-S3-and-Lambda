import boto3
import os
import tempfile
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
            with tempfile.NamedTemporaryFile() as tmp_in, tempfile.NamedTemporaryFile(suffix=".jpg") as tmp_out:
                # Download original image
                try:
                    s3.download_file(src_bucket, src_key, tmp_in.name)
                    logger.info(f"Successfully downloaded {src_key}")
                except Exception as e:
                    logger.error(f"Error downloading {src_key}: {e}")
                    continue # Skip to the next record

                # Open and process image
                try:
                    with Image.open(tmp_in.name) as img:
                        original_width, original_height = img.size
                        # Dummy processing: resize and compress
                        img = img.resize((img.width // 2, img.height // 2))
                        processed_width, processed_height = img.size
                        img.save(tmp_out.name, "JPEG", optimize=True, quality=70)
                    logger.info(f"Successfully processed {src_key}")
                except Exception as e:
                    logger.error(f"Error processing image {src_key}: {e}")
                    continue # Skip to the next record

                # Upload processed image to target bucket
                dest_key = f"processed-{os.path.basename(src_key)}"
                try:
                    s3.upload_file(tmp_out.name, processed_bucket, dest_key)
                    processed_file_size = os.path.getsize(tmp_out.name)
                    logger.info(f"Successfully uploaded processed image {dest_key} to {processed_bucket}")
                except Exception as e:
                    logger.error(f"Error uploading processed image {dest_key}: {e}")
                    continue # Skip to the next record

                # Store metadata in DynamoDB
                try:
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
                    logger.error(f"Error storing metadata for {src_key} in DynamoDB: {e}")
                    continue # Skip to the next record

        except Exception as e:
            logger.critical(f"Unhandled error processing record for {src_key}: {e}")

    return {
        'statusCode': 200,
        'body': 'Image processing complete'
    }
