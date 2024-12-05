import os
import json
import hashlib
import requests
import boto3
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from datetime import datetime
from FetchPRComments import triggerGitAPIPullPRComments, fetchReusableMethodsFromAutomationRepo
from langchain_aws import BedrockEmbeddings

# AWS S3 bucket details
S3_BUCKET_NAME = "uploadchromedatabasecontent"
S3_REGION = "us-west-2"

# Initialize S3 client
s3_client = boto3.client('s3', region_name=S3_REGION)

# Base directory for metadata
ROOT_DIRECTORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIRECTORY = os.path.join(ROOT_DIRECTORY, "src", "vectors")
METADATA_FILE = os.path.join(BASE_DIRECTORY, 'vectorized_metadata.json')

# Vector storage subfolders (used to categorize context types)
VECTOR_CATEGORIES = {
    "old_codes": "old_codes",
    "coding_standards": "coding_standards",
    "review_comments": "review_comments",
    "reusable_utilities": "reusable_utilities"
}

# Ensure directories and metadata file exist locally (optional for debugging)
def ensure_directories():
    os.makedirs(BASE_DIRECTORY, exist_ok=True)
    if not os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'w') as f:
            json.dump({}, f)

# Load metadata (tracks files and their hashes)
def load_metadata():
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r') as f:
            return json.load(f)
    return {}

# Save metadata
def save_metadata(metadata):
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=4)

# Generate a unique hash for content
def generate_content_hash(content):
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

# Check if content has been modified based on its hash
def is_content_modified(content_hash, content_id, metadata):
    return metadata.get(content_id) != content_hash

# Upload content to S3
def upload_to_s3(content, category, content_id):
    s3_key = f"{category}/{content_id}.json"
    content_data = json.dumps(content)
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=content_data,
            ContentType="application/json"
        )
        print(f"[INFO] Uploaded {s3_key} to S3.")
    except Exception as e:
        print(f"[ERROR] Failed to upload {s3_key}: {e}")

# Vectorize and upload content
def vectorize_and_upload_content(content, content_id, category, metadata, embedding_function):
    if not content.strip():
        print(f"[WARNING] Content for {content_id} is empty, skipping vectorization.")
        return

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = [Document(page_content=content)]
    splits = splitter.split_documents(docs)

    if not splits:
        print(f"[WARNING] No splits created for {content_id}, skipping vectorization.")
        return

    split_texts = [split.page_content for split in splits]
    embedding_data = {"chunks": split_texts}

    upload_to_s3(embedding_data, category, content_id)
    metadata[content_id] = generate_content_hash(content)

# Fetch Google coding standards
def fetch_google_coding_standards():
    url = "https://google.github.io/styleguide/javaguide.html"
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    return ""

# Main context setup function
def setup_context(reference_files, google_coding_url, previous_review_json, reusable_utilities_json):
    ensure_directories()
    metadata = load_metadata()
    embedding_function = BedrockEmbeddings(credentials_profile_name='default', model_id='amazon.titan-embed-text-v1')

    # Process reference files
    for idx, ref_content in enumerate(reference_files):
        content_id = f"Reference_{idx}"
        content = ref_content.get("content", "")
        content_hash = generate_content_hash(content)
        if is_content_modified(content_hash, content_id, metadata):
            vectorize_and_upload_content(content, content_id, VECTOR_CATEGORIES["old_codes"], metadata, embedding_function)

    # Process Google coding standards
    google_coding_content = fetch_google_coding_standards()
    content_hash = generate_content_hash(google_coding_content)
    if is_content_modified(content_hash, "Google_Coding_Standards", metadata):
        vectorize_and_upload_content(google_coding_content, "Google_Coding_Standards", VECTOR_CATEGORIES["coding_standards"], metadata, embedding_function)

    # Function to Process Previous PR Comments
    for repo_data in previous_review_json:
        pr_comments = repo_data.get("prComments", [])
        for idx, pr_comment in enumerate(pr_comments):
            comment_text = pr_comment.get("comment", "")
            code_snippet = pr_comment.get("code_snippet", "")

            # Debug logs to trace values
            print(f"Master Log - PR Comment Text: {comment_text}")
            print(f"Master Log - PR Code Snippet: {code_snippet}")

            # Generate unique IDs for comment and snippet
            comment_id = f"PR_Comment_{idx}_Text"
            snippet_id = f"PR_Comment_{idx}_Snippet"

            # Generate hashes for the content
            comment_hash = generate_content_hash(comment_text)
            snippet_hash = generate_content_hash(code_snippet)

            # Debug logs for hash
            print(f"Master Log - Comment Hash: {comment_hash}")
            print(f"Master Log - Snippet Hash: {snippet_hash}")

            # Only vectorize if the content has been modified
            if comment_text and is_content_modified(comment_hash, comment_id, metadata):
                vectorize_and_upload_content(comment_text, comment_id, VECTOR_CATEGORIES["review_comments"], metadata, embedding_function)
            if code_snippet and is_content_modified(snippet_hash, snippet_id, metadata):
                vectorize_and_upload_content(code_snippet, snippet_id, VECTOR_CATEGORIES["review_comments"], metadata, embedding_function)

            # Save updated metadata after processing all comments
            save_metadata(metadata)
            print("[INFO] Context setup completed.")

    

    # Process reusable utilities
    for idx, utility in enumerate(reusable_utilities_json):
        content_id = f"Reusable_Utility_{idx}"
        utility_text = utility if isinstance(utility, str) else ""
        content_hash = generate_content_hash(utility_text)
        print("Master Log - Process reusable utilities",f" Comment Text: {utility_text}")
        print("Master Log - Process reusable utilities",f" Code Snippet: {content_id}")
        print("Master Log - Process reusable utilities",f" Code Snippet: {content_hash}")
        if is_content_modified(content_hash, content_id, metadata):
            vectorize_and_upload_content(utility_text, content_id, VECTOR_CATEGORIES["reusable_utilities"], metadata, embedding_function)

    save_metadata(metadata)
    print("[INFO] Context setup completed.")

    




# Example run
if __name__ == "__main__":
    previous_review_json = triggerGitAPIPullPRComments()
    print('Master Log - triggerGitAPIPullPRComments()' , previous_review_json)
    reusable_utilities_json = fetchReusableMethodsFromAutomationRepo()

    reference_files = [
        {"content": "public class Example { }"},
        {"content": "public interface TestInterface { }"}
    ]

    setup_context(reference_files, "", previous_review_json, reusable_utilities_json)


