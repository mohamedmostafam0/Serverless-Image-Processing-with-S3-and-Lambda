# Serverless Image Processing Application

This project is a serverless application for processing images uploaded to an Amazon S3 bucket. When a user uploads an image, an AWS Lambda function is automatically triggered to resize and watermark the image, storing the processed version in a separate S3 bucket.

## Architecture

The application follows a serverless, event-driven architecture.

1.  **Image Upload:** A user uploads an image file to the source Amazon S3 bucket.
2.  **Lambda Trigger:** The S3 upload event triggers an AWS Lambda function.
3.  **Image Processing:** The Lambda function, using libraries like Sharp, processes the image. This includes resizing the image to a standard format and adding a watermark.
4.  **Processed Image Storage:** The processed image is then saved to a destination S3 bucket.

![Architecture Diagram](architecture_diagram.drawio.png)

## Key AWS Services Used

- **Amazon S3:** Used for storing both the original and the processed images.
- **AWS Lambda:** The core of the application, running the image processing code without the need for a dedicated server.
- **Amazon API Gateway:** To create an API for image uploads.
- **Amazon DynamoDB:** For storing image metadata.

## Features

- **Automatic Image Resizing:** Images are automatically resized to predefined dimensions.
- **Serverless:** No servers to manage, leading to reduced operational overhead.
- **Scalable:** The architecture can handle a high volume of image uploads.
- **Cost-Effective:** Pay only for the compute time and storage used.

## Getting Started

### Prerequisites

- An AWS Account
- Node.js and npm installed
- AWS CLI configured on your local machine
- Serverless Framework or AWS SAM CLI (optional, for deployment)

## Usage

Once deployed, you can use the application by uploading an image to the designated source S3 bucket. The processed image will appear in the destination S3 bucket shortly after.

## Contributing

Contributions are welcome! Please feel free to submit a pull request.
