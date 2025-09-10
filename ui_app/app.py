from flask import Flask, request, render_template, jsonify
import requests
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import os
import urllib.parse

app = Flask(__name__)

# --- Configuration (Replace with your actual API Gateway URL) ---
API_GATEWAY_URL = "https://8jzs16qcj9.execute-api.us-east-1.amazonaws.com/prod/upload/"

# --- AWS Session and Credentials ---
session = boto3.Session()
credentials = session.get_credentials()
region = session.region_name

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        image_data = image_file.read()
        s3_object_key = urllib.parse.unquote(image_file.filename)
        content_type = image_file.content_type

        url = API_GATEWAY_URL + s3_object_key
        method = "PUT"

        # Create an AWSRequest object
        aws_request = AWSRequest(
            method=method,
            url=url,
            data=image_data,
            headers={'Content-Type': content_type}
        )

        # Sign the request
        SigV4Auth(credentials, 'execute-api', region).add_auth(aws_request)

        # Convert AWSRequest to requests.Request
        prepared_request = requests.Request(
            method=aws_request.method,
            url=aws_request.url,
            headers=aws_request.headers,
            data=aws_request.body
        ).prepare()

        # Send the request
        response = requests.Session().send(prepared_request)

        if response.status_code == 200:
            return jsonify({"message": f"Successfully uploaded {s3_object_key}"}), 200
        else:
            return jsonify({"error": f"Failed to upload image: {response.text}"}), response.status_code

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
