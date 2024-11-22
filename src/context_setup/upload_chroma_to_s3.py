import os
import boto3

# AWS S3 bucket name
S3_BUCKET_NAME = "uploadchromadbcontext"

# Initialize S3 client
s3_client = boto3.client('s3', region_name='us-west-2')  # Add your AWS region

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
    BASE_DIRECTORY = ""  # Local directory path (/path/to/your/local/chroma_db)
    upload_chroma_db_to_s3(BASE_DIRECTORY)
# Upload specifix file into s3
# if __name__ == "__main__":
#     FILE_PATH = r"C:\Users\2280571\Downloads\Sealights Configuration.xlsx"  # Path to your file
#     S3_KEY = os.path.basename(FILE_PATH)  # S3 key (file name in S3)
#     upload_to_s3(FILE_PATH, S3_BUCKET_NAME, S3_KEY)
