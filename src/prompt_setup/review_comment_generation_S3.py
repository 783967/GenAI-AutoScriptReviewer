import os
import boto3
from langchain.prompts import PromptTemplate
from langchain_aws import ChatBedrock
from langchain_chroma import Chroma
from langchain.schema import AIMessage
from langchain_aws import BedrockEmbeddings
import sys
import tempfile

current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(src_dir)

from context_setup.FetchPRComments import *

# S3 Configuration
s3_client = boto3.client('s3', region_name='us-west-2')
S3_BUCKET_NAME = "uploadchromedatabasecontent"
S3_VECTORS_PREFIX = "vectors"

# Temporary directory for storing downloaded vectors
TEMP_DIR = tempfile.mkdtemp()


# Function to download vectors from S3 to a local directory
def download_vectors_from_s3(s3_prefix, local_directory):
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=s3_prefix)

    for page in pages:
        if 'Contents' in page:
            for obj in page['Contents']:
                s3_key = obj['Key']
                relative_path = os.path.relpath(s3_key, s3_prefix)
                local_file_path = os.path.join(local_directory, relative_path)

                os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

                # Download each file from S3
                s3_client.download_file(S3_BUCKET_NAME, s3_key, local_file_path)


# Function to load Chroma DB from the downloaded vectors
def load_chroma_db(s3_prefix):
    local_directory = os.path.join(TEMP_DIR, os.path.basename(s3_prefix))
    download_vectors_from_s3(s3_prefix, local_directory)
    embedding_function = BedrockEmbeddings(credentials_profile_name='default', model_id='amazon.titan-embed-text-v1')
    return Chroma(persist_directory=local_directory, embedding_function=embedding_function)


# Load new code from a file
def load_new_code(file_path):
    with open(file_path, 'r') as file:
        return file.read()


# Query for similarity search in a specific Chroma DB
def query_similar_code(chroma_db, new_code_content):
    results = chroma_db.similarity_search(new_code_content, k=3)
    return results


# Setup LLM
def setup_llm():
    client = boto3.client('bedrock-runtime', region_name='us-west-2')
    llm = ChatBedrock(
        credentials_profile_name='default',
        model_id='anthropic.claude-3-5-sonnet-20241022-v2:0',
        client=client
    )
    return llm


# Run the code review with multiple contexts
def run_code_review(llm, new_code, contexts):
    print('Prompt feed to LLM')
    template = """
    You are a **Java Code Review Assistant** with extensive experience in reviewing automation testing code, focusing on code quality, reusability, adherence to coding standards, and leveraging existing utilities for efficiency. Your expertise spans various testing frameworks, automation libraries, and design patterns in test automation.
 
    Your role is to assist developers by providing **accurate, context-aware review comments**. Use the provided reference contexts to evaluate the new code carefully, and suggest actionable improvements.
 
    **Reference Contexts**:
    
    1. **Old Codes**: {old_codes}
    2. **Google Coding Standards**: {google_coding_standards}
    3. **Previous Review Comments**: {review_comments}
    4. **Reusable Utilities**: {reusable_utilities}
 
    --- 
 
    ### New Code to Review:
    {new_code}
 
    **Review Instructions**:
 
    - For each issue found, provide detailed feedback in the following format:
      - **File Path**: Provide the complete path from the project root to the file where the issue is located.
      - **Line Number**: Specify the exact line number where the issue occurs. Use the logic described below to derive line numbers:
        - **Logic for Line Numbers**:
            - Use the `git diff` syntax provided in the context (e.g., `@@ -19,6 +19,8`).
            - Identify the starting line number in the updated file (`+19` in this example).
            - Add offsets to the starting line number for each subsequent line in the code snippet to pinpoint the exact location.
            - When a range of lines (e.g., `@@ -63,7 +65,7`) is provided, ensure the exact line number is calculated within this range. 
            - For example:
                - If an issue occurs on the third line of a snippet starting at `+19`, the exact line number is `19 + 2 = 21`.
                - If an issue occurs on the first line in the range starting at `+65`, the line number is `65`.
            - Ensure precise calculations to avoid discrepancies.

      - **Issue Description**: 
        - Clearly and concisely describe the issue.
        - If it violates Google coding standards, explicitly state: "As per Google coding standards, this is incorrect."
        - If a reusable utility already exists for a custom method, suggest using the existing utility:
          - Provide the method name and the full file path of the utility.
        - If there is no reusable utility and the method is valid, acknowledge that creating a new method is acceptable.
        - Check **Previous Review Comments** for recurring issues or patterns and validate whether similar issues are present in the new code.
    
        - If the code is correct:
        - Do not provide feedback. Clearly acknowledge the code is correct without suggesting unnecessary changes.

 
    - **Tone of Feedback**: 
      - Follow the professional tone and structure from **Previous Review Comments** where applicable.
      - Be precise, clear, and concise. Avoid vague statements and redundant explanations.
 
    - **Do Not**: 
      - Suggest personal opinions or preferences.
      - Recommend changes outside the scope of the provided contexts.
 
    **Example Feedback Format**:
 
    ```
    - **File Path**: src/main/java/com/projectname/module/ClassName.java
    - **Line Number**: 45
    - **Issue**: Method `validateInput()` duplicates functionality available in the reusable utility `InputValidator.validate()`. 
      Suggested Utility: `src/main/java/com/projectname/utils/InputValidator.java`.
      As per Google coding standards, this is incorrect. Please use the existing utility for consistency and maintainability.
    ```
"""
    prompt = PromptTemplate(
        template=template,
        input_variables=["old_codes", "google_coding_standards", "review_comments", "reusable_utilities", "new_code"]
    )

    reference_context = {
        "old_codes": "\n\n".join([doc.page_content for doc in contexts['old_codes']]),
        "google_coding_standards": "\n\n".join([doc.page_content for doc in contexts['google_coding_standards']]),
        "review_comments": "\n\n".join([doc.page_content for doc in contexts['review_comments']]),
        "reusable_utilities": "\n\n".join([doc.page_content for doc in contexts['reusable_utilities']]),
        "new_code": new_code
    }
    print('Prompt feed to LLM2')
    sequence = prompt | llm
    review = sequence.invoke(reference_context)
    print('Prompt feed to LLM3')
    return review


# Perform the code review
def code_review(new_code_files):
    reviews = []
    new_code_content = new_code_files
   
    # Load contexts from different Chroma DBs
    contexts = {
        "old_codes": query_similar_code(load_chroma_db(f"{S3_VECTORS_PREFIX}/old_codes"), new_code_content),
        "google_coding_standards": query_similar_code(load_chroma_db(f"{S3_VECTORS_PREFIX}/coding_standards"), new_code_content),
        "review_comments": query_similar_code(load_chroma_db(f"{S3_VECTORS_PREFIX}/review_comments"), new_code_content),
        "reusable_utilities": query_similar_code(load_chroma_db(f"{S3_VECTORS_PREFIX}/reusable_utilities"), new_code_content),
    }
   
    # Setup LLM and run review for the current file
    llm = setup_llm()
    review_comment = run_code_review(llm, new_code_content, contexts)
    reviews.append(review_comment.content)
   
    return "\n\n".join(reviews)


# Main function
if __name__ == "__main__":
    # Fetch files from PR (returns a list of file contents)
    new_code_files = fetchDiffFromPR(4)
    print(new_code_files)
    # Run the code review for all files
    review_comments = code_review(new_code_files)
    print(f"Review Comments:\n{review_comments}")

