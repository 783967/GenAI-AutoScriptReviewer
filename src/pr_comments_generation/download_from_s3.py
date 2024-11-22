import os
import boto3

# AWS S3 bucket name
S3_BUCKET_NAME = "uploadchromadbcontext"

# Initialize S3 client
s3_client = boto3.client('s3', region_name='us-west-2')  # Add your AWS region

# This function downloads a file from S3
def download_from_s3(bucket_name, s3_key, download_path):
    try:
        s3_client.download_file(bucket_name, s3_key, download_path)
        print(f"Successfully downloaded {s3_key} from {bucket_name} to {download_path}")
    except Exception as e:
        print(f"Error downloading {s3_key} from S3: {e}")

# Example usage
if __name__ == "__main__":
    ROOT_DIRECTORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Dynamic root directory path
    base_persistent_dir = os.path.join(ROOT_DIRECTORY, "src", "vectors")

    # Define additional directories
    old_code_dir = os.path.join(base_persistent_dir, "old_codes")
    coding_standards_dir = os.path.join(base_persistent_dir, "coding_standards")
    review_comments_dir = os.path.join(base_persistent_dir, "review_comments")
    reusable_utilities_dir = os.path.join(base_persistent_dir, "reusable_utilities")

    # Ensure all directories exist
    os.makedirs(base_persistent_dir, exist_ok=True)
    os.makedirs(old_code_dir, exist_ok=True)
    os.makedirs(coding_standards_dir, exist_ok=True)
    os.makedirs(review_comments_dir, exist_ok=True)
    os.makedirs(reusable_utilities_dir, exist_ok=True)

    # Prompt user for the S3 key (file name in S3)
    S3_KEY = input("Enter the S3 key (file name) to download: ")
    DOWNLOAD_PATH = os.path.join(base_persistent_dir, S3_KEY)  # Local path to save the downloaded file

    download_from_s3(S3_BUCKET_NAME, S3_KEY, DOWNLOAD_PATH)
