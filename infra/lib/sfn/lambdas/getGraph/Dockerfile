# Use an official Python runtime as a parent image
FROM public.ecr.aws/lambda/python:3.10

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any needed dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the local code to the container image
COPY lambda_function.py .

# Set the CMD to your handler
CMD ["lambda_function.lambda_handler"]
