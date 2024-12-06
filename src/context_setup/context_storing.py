import os  # For working with file system paths and directories
import json  # For reading and writing JSON files (metadata)
import requests  # For making HTTP requests to fetch external content
from langchain.text_splitter import RecursiveCharacterTextSplitter  # For splitting text into chunks for vectorization
from langchain_aws import BedrockEmbeddings  # For embedding text using Amazon Bedrock
from langchain_chroma import Chroma  # For storing and retrieving embeddings in a vector database
from datetime import datetime  # For working with timestamps (not used here)
from langchain.schema import Document  # For creating document objects with content and metadata
from FetchPRComments import (  # Custom functions to fetch previous review comments and reusable utilities
    triggerGitAPIPullPRComments, 
    fetchReusableMethodsFromAutomationRepo
)

# Get the dynamic base directory, which is the root of the project
ROOT_DIRECTORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Set the base directory where all vectorized data will be stored
BASE_DIRECTORY = os.path.join(ROOT_DIRECTORY, "src", "vectors")

# Define paths for different vector storage subfolders
OLD_CODES_DIR = os.path.join(BASE_DIRECTORY, "old_codes")  # Directory for storing vectors of old reference code
CODING_STANDARDS_DIR = os.path.join(BASE_DIRECTORY, "coding_standards")  # Directory for Google coding standards vectors
REVIEW_COMMENTS_DIR = os.path.join(BASE_DIRECTORY, "review_comments")  # Directory for vectors of previous review comments
REUSABLE_UTILITIES_DIR = os.path.join(BASE_DIRECTORY, "reusable_utilities")  # Directory for reusable utility vectors

# File to store metadata that tracks which files have been vectorized and their content hashes
METADATA_FILE = os.path.join(BASE_DIRECTORY, 'vectorized_metadata.json')

# Ensure all necessary directories for storing vectors exist
def ensure_directories():
    os.makedirs(OLD_CODES_DIR, exist_ok=True)
    os.makedirs(CODING_STANDARDS_DIR, exist_ok=True)
    os.makedirs(REVIEW_COMMENTS_DIR, exist_ok=True)
    os.makedirs(REUSABLE_UTILITIES_DIR, exist_ok=True)
    print("[INFO] Directories ensured.")  # Confirmation that all directories are created

# Load metadata file if it exists, which tracks previously vectorized files and their content hashes
def load_metadata():
    if os.path.exists(METADATA_FILE):  # Check if the metadata file exists
        with open(METADATA_FILE, 'r') as f:  # Open the metadata file in read mode
            print("[INFO] Metadata loaded.")  # Log message indicating metadata is loaded
            return json.load(f)  # Load the JSON data and return it as a dictionary
    print("[INFO] No metadata found, initializing new metadata.")  # Log if no metadata file is found
    return {}  # Return an empty dictionary if no metadata file exists

# Save the updated metadata back to the file
def save_metadata(metadata):
    with open(METADATA_FILE, 'w') as f:  # Open the metadata file in write mode
        json.dump(metadata, f, indent=4)  # Save the metadata dictionary as a JSON file
    print("[INFO] Metadata saved.")  # Log message indicating metadata has been saved

# Check if the content of a file or data is modified by comparing its hash
def is_content_modified(content, content_id, metadata):
    content_hash = hash(content)  # Generate a hash of the content
    if content_id in metadata and metadata[content_id] == content_hash:  # Check if the hash matches the metadata
        return False  # If the hash matches, the content is not modified
    return True  # If the hash doesn't match, the content is modified

# Function to load and vectorize new or modified content
def load_and_vectorize_new_content(content, content_id, metadata, embedding_function, directory):
    # Ensure the target directory exists
    os.makedirs(directory, exist_ok=True)

    if not content.strip():  # Check if the content is empty or only contains whitespace
        print(f"[WARNING] Content for {content_id} is empty, skipping vectorization.")  # Log warning for empty content
        return

    # Initialize a text splitter to split large content into smaller chunks for vectorization
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

    # Wrap the content in a Document object (LangChain schema), along with metadata
    docs = [Document(page_content=content, metadata=metadata)]

    # Split the document into smaller chunks based on the splitter settings
    splits = splitter.split_documents(docs)

    if not splits:  # Check if the splitting process resulted in any chunks
        print(f"[WARNING] No splits created for {content_id}, skipping vectorization.")  # Log warning if no splits
        return

    # Extract the text content from each split for embedding
    split_texts = [split.page_content for split in splits]

    print(f"[INFO] Splitting content ID '{content_id}' into {len(split_texts)} chunks.")  # Log split information

    # Initialize a Chroma database object for storing embeddings
    chroma_db = Chroma(persist_directory=directory, embedding_function=embedding_function)
    try:
        # Add the split texts to the Chroma database with unique IDs
        chroma_db.add_texts(split_texts, ids=[f"{content_id}_{i}" for i in range(len(split_texts))])
        print(f"[INFO] Embedded and stored content for '{content_id}' in '{directory}'.")  # Log success
    except Exception as e:
        print(f"[ERROR] Failed to embed content for {content_id}: {e}")  # Log any errors during embedding

# Fetch Google coding standards from a predefined URL
def fetch_google_coding_standards():
    url = "https://google.github.io/styleguide/javaguide.html"  # URL for Google's Java coding standards
    response = requests.get(url)  # Make an HTTP GET request to fetch the content
    if response.status_code == 200:  # Check if the request was successful
        print("[INFO] Fetched Google Coding Standards.")  # Log success
        return response.text  # Return the fetched content as text
    else:
        print(f"[ERROR] Failed to fetch Google Coding Standards. Status Code: {response.status_code}")  # Log error
        return ""  # Return empty string if the request failed

# Set up context by embedding new or modified files for each type of content
def setup_context(reference_files, google_coding_url, previous_review_json, reusable_utilities_json):
    ensure_directories()  # Ensure required directories are created
    metadata = load_metadata()  # Load existing metadata to track vectorization
    embedding_function = BedrockEmbeddings(credentials_profile_name='default', model_id='amazon.titan-embed-text-v1')

    # Process each reference file provided in the input
    for idx, ref_content in enumerate(reference_files):
        print(f"[INFO] Processing Reference File {idx}")
        #print("Master Log - Process each reference file provided in the input ",ref_content.get("content", ""))
        load_and_vectorize_new_content(ref_content.get("content", ""), f"Reference_{idx}", metadata, embedding_function, OLD_CODES_DIR)

    # Process Google coding standards content
    google_coding_content = fetch_google_coding_standards()
    #print("Master Log - Process Google coding standards content ",google_coding_content)
    load_and_vectorize_new_content(google_coding_content, "Google_Coding_Standards", metadata, embedding_function, CODING_STANDARDS_DIR)

    # Process previous pull request (PR) comments fetched from GitHub
    for repo_data in previous_review_json:
        pr_comments = repo_data.get("prComments", [])
        for idx, pr_comment in enumerate(pr_comments):
            comment_text = pr_comment.get("comment", "")
            code_snippet = pr_comment.get("code_snippet", "")

            # Print to debug
            #print("Master Log - Process previous pull request (PR) comments fetched from GitHub",f" Comment Text: {comment_text}")
            #print("Master Log - Process previous pull request (PR) comments fetched from GitHub",f" Code Snippet: {code_snippet}")

            if comment_text:
                load_and_vectorize_new_content(comment_text, f"PR_Comment_{idx}_Text", metadata, embedding_function, REVIEW_COMMENTS_DIR)
            if code_snippet:
                load_and_vectorize_new_content(code_snippet, f"PR_Comment_{idx}_Snippet", metadata, embedding_function, REVIEW_COMMENTS_DIR)

    # Process reusable utilities fetched from the automation repository
    for idx, utility in enumerate(reusable_utilities_json):
        if isinstance(utility, str):
            utility_text = utility
        elif isinstance(utility, dict) and 'content' in utility:
            utility_text = utility['content']
        else:
            print(f"[ERROR] Utility at index {idx} is not a valid format: {type(utility)}")
            continue

        #print('Master Log - Process reusable utilities fetched from the automation repository',utility_text)
        load_and_vectorize_new_content(utility_text, f"Reusable_Utility_{idx}", metadata, embedding_function, REUSABLE_UTILITIES_DIR)

    save_metadata(metadata)  # Save updated metadata after vectorization
    print("[INFO] Context setup completed.")  # Log completion

# Main block to run the setup process when the script is executed directly
if __name__ == "__main__":
    previous_review_json = triggerGitAPIPullPRComments()  # Fetch previous review comments
    #print('Master Log - triggerGitAPIPullPRComments()' , previous_review_json)
    reusable_utilities_json = fetchReusableMethodsFromAutomationRepo()  # Fetch reusable methods from repo
    #print('Master Log - fetchReusableMethodsFromAutomationRepo()' , reusable_utilities_json)
    
    reference_files = [  # Example mock reference files (replace with dynamic content)
        {"content": "public class Example { }"},
        {"content": "public interface TestInterface { }"}
    ]
    setup_context(reference_files, "", previous_review_json, reusable_utilities_json)  # Trigger the setup process



