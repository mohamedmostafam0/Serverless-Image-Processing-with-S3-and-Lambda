FROM public.ecr.aws/lambda/python:3.11

# Create and set the working directory
WORKDIR /asset

# Copy the requirements file
COPY requirements.txt .

# Install dependencies into the asset directory
RUN pip install -r requirements.txt -t .

# Copy the Lambda function code
COPY lambda_function.py .
