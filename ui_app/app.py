from flask import Flask, request, jsonify, render_template
import boto3
from botocore.exceptions import ClientError
import os

app = Flask(__name__)

# --- Configuration ---
# These should match the bucket names in your CDK stack
UPLOAD_BUCKET = "uploaded-images-bucket-20250910"
PROCESSED_BUCKET = "processed-images-bucket-20250910"
REGION = boto3.Session().region_name or "us-east-1"

s3_client = boto3.client('s3', region_name=REGION)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate-upload-url')
def generate_upload_url():
    filename = request.args.get('filename')
    content_type = request.args.get('contentType')

    if not filename or not content_type:
        return jsonify({"error": "Missing filename or contentType"}), 400

    try:
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': UPLOAD_BUCKET,
                'Key': filename,
                'ContentType': content_type
            },
            ExpiresIn=3600  # URL expires in 1 hour
        )
        return jsonify({"url": presigned_url})
    except ClientError as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get-processed-image-url')
def get_processed_image_url():
    filename = request.args.get('filename')
    if not filename:
        return jsonify({"error": "Missing filename"}), 400

    try:
        # First, check if the object exists
        s3_client.head_object(Bucket=PROCESSED_BUCKET, Key=filename)

        # If it exists, generate the presigned URL
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': PROCESSED_BUCKET,
                'Key': filename
            },
            ExpiresIn=3600 # URL expires in 1 hour
        )
        return jsonify({"url": presigned_url})
    except ClientError as e:
        # If the error is a 404 Not Found, it means the file is not processed yet
        if e.response['Error']['Code'] == '404':
            return jsonify({"error": "File not found"}), 404
        # For other errors, return a 500
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)