import os
import json
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_aws import BedrockEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import TextLoader
from datetime import datetime
from FetchPRComments import *

# Get dynamic base directory (root of the project)
ROOT_DIRECTORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIRECTORY = os.path.join(ROOT_DIRECTORY, "src", "vectors")


# Paths for different vector storage subfolders
OLD_CODES_DIR = os.path.join(BASE_DIRECTORY, "old_codes")
CODING_STANDARDS_DIR = os.path.join(BASE_DIRECTORY, "coding_standards")
REVIEW_COMMENTS_DIR = os.path.join(BASE_DIRECTORY, "review_comments")
REUSABLE_UTILITIES_DIR = os.path.join(BASE_DIRECTORY, "reusable_utilities")

# Metadata file to track vectorized files
METADATA_FILE = os.path.join(BASE_DIRECTORY, 'vectorized_metadata.json')

# This function ensures that the necessary directories exist
def ensure_directories():
    if not os.path.exists(BASE_DIRECTORY):
        os.makedirs(BASE_DIRECTORY)  # Create base directory if it doesn't exist
    os.makedirs(OLD_CODES_DIR, exist_ok=True)
    os.makedirs(CODING_STANDARDS_DIR, exist_ok=True)
    os.makedirs(REVIEW_COMMENTS_DIR, exist_ok=True)
    os.makedirs(REUSABLE_UTILITIES_DIR, exist_ok=True)

# This function loads the metadata file if it exists
def load_metadata():
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r') as f:
            return json.load(f)
    return {}

# This function saves the metadata to track vectorized files
def save_metadata(metadata):
    # Create the directory if it doesn't exist
    directory = os.path.dirname(METADATA_FILE)
    if not os.path.exists(directory):
        os.makedirs(directory)  # Create the directory if it doesn't exist
    
    # Save the metadata file
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=4)

# Check if the file is new or has been modified since the last vectorization
def is_file_modified(file_path, metadata):
    last_modified_time = os.path.getmtime(file_path)  # Get the last modified timestamp
    file_name = os.path.basename(file_path)

    # Check if the file exists in metadata and compare its timestamp
    if file_name in metadata and metadata[file_name] == last_modified_time:
        return False  # File hasn't changed, no need to vectorize
    return True  # File is new or modified

# This function loads only new or modified files for vectorization
def load_new_or_modified_files(file_paths, metadata):
    new_docs = []
    for file_path in file_paths:
        if is_file_modified(file_path, metadata):
            loader = TextLoader(file_path)
            new_docs.extend(loader.load())
    return new_docs

# Same as previous but modified to handle new files only
def split_context(docs):
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    return splitter.split_documents(docs)

# This function adds only the new documents to Chroma DB
def store_new_context_in_chroma(splits, embedding_function, persist_directory):
    chroma_db = Chroma(persist_directory=persist_directory, embedding_function=embedding_function)
    chroma_db.add_texts([doc.page_content for doc in splits])  # Add new splits to the existing DB
    return chroma_db

# This function sets up the context for newly added or modified files
def setup_context(reference_files, google_coding_url, previous_review_json, reusable_utilities_json):
    ensure_directories()  # Ensure the base directory and subdirectories exist
    metadata = load_metadata()  # Load the previous metadata
    
    # Step 1: Load new or modified files
    new_context_docs = load_new_or_modified_files(reference_files, metadata)
    
    if not new_context_docs:
        print("No new or modified files to vectorize.")
        return None

    # Step 2: Split the new files into smaller chunks
    context_splits = split_context(new_context_docs)
    
    # Step 3: Use Amazon Bedrock to generate embeddings
    embeddings_function = BedrockEmbeddings(credentials_profile_name='default', model_id='amazon.titan-embed-text-v1')

    # Step 4: Store only new splits in Chroma DB in separate folders for different contexts
    store_new_context_in_chroma(context_splits, embeddings_function, OLD_CODES_DIR)
    store_new_context_in_chroma(context_splits, embeddings_function, CODING_STANDARDS_DIR)
    store_new_context_in_chroma(context_splits, embeddings_function, REVIEW_COMMENTS_DIR)
    store_new_context_in_chroma(context_splits, embeddings_function, REUSABLE_UTILITIES_DIR)
    
    # Update metadata with the newly vectorized files' information
    for file_path in reference_files:
        file_name = os.path.basename(file_path)
        metadata[file_name] = os.path.getmtime(file_path)  # Store last modified time
    
    # Save updated metadata
    save_metadata(metadata)
    
    return True

# Example to run the setup
if __name__ == "__main__":
    # Reference files
    reference_files = 'null' #Existing code in the repository
    previous_review_json = triggerGitAPIPullPRComments() #Giving previous PR comments 
    reusable_utilities_json = fetchReusableMethodsFromAutomationRepo() #src/main/Java utilities
    
    setup_context(reference_files, "https://google.github.io/styleguide/javaguide.html", previous_review_json, reusable_utilities_json)
