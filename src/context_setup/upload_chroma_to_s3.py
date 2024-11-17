import os
import json
import boto3
from langchain_chroma import Chroma

# AWS S3 bucket name
S3_BUCKET_NAME = "uploadchromadbcontext"

# Initialize S3 client
s3_client = boto3.client('s3')

# This function uploads a file to S3
def upload_to_s3(file_path, bucket_name, s3_key):
    try:
        s3_client.upload_file(file_path, bucket_name, s3_key)
        print(f"Successfully uploaded {file_path} to {bucket_name}/{s3_key}")
    except Exception as e:
        print(f"Error uploading {file_path} to S3: {e}")

# This function uploads the Chroma DB content to S3
def upload_chroma_db_to_s3(base_directory):
    for root, dirs, files in os.walk(base_directory):
        for file in files:
            file_path = os.path.join(root, file)
            s3_key = os.path.relpath(file_path, base_directory)
            upload_to_s3(file_path, S3_BUCKET_NAME, s3_key)

# Example usage
if __name__ == "__main__":
    BASE_DIRECTORY = "s3://uploadchromadbcontext/chroma_db/"
    upload_chroma_db_to_s3(BASE_DIRECTORY)
