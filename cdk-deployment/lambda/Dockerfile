FROM public.ecr.aws/lambda/python:3.11

# Copy function code
COPY lambda_function.py ${LAMBDA_TASK_ROOT}

# Install the specified packages
COPY requirements.txt .
RUN pip install -r requirements.txt --target ${LAMBDA_TASK_ROOT}
