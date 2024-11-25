import os
from langchain.prompts import PromptTemplate
from langchain_aws import ChatBedrock
from langchain_chroma import Chroma
from langchain.schema import AIMessage
import boto3
from langchain_aws import BedrockEmbeddings
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(src_dir)

from context_setup.FetchPRComments import *

# Get dynamic base directory (root of the project)
ROOT_DIRECTORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
base_persistent_dir = os.path.join(ROOT_DIRECTORY, "S3FilesForChromaDb", "vectors")

old_code_dir = os.path.join(base_persistent_dir, "old_codes")
coding_standards_dir = os.path.join(base_persistent_dir, "coding_standards")
review_comments_dir = os.path.join(base_persistent_dir, "review_comments")
reusable_utilities_dir = os.path.join(base_persistent_dir, "reusable_utilities")

# Ensure these directories exist
os.makedirs(old_code_dir, exist_ok=True)
os.makedirs(coding_standards_dir, exist_ok=True)
os.makedirs(review_comments_dir, exist_ok=True)
os.makedirs(reusable_utilities_dir, exist_ok=True)

# Load new code from a file
def load_new_code(file_path):
    with open(file_path, 'r') as file:
        return file.read()

# Load Chroma DB for different contexts
def load_chroma_db(persist_directory):
    embedding_function = BedrockEmbeddings(credentials_profile_name='default', model_id='amazon.titan-embed-text-v1')
    return Chroma(persist_directory=persist_directory, embedding_function=embedding_function)

# Query for similarity search in a specific Chroma DB
def query_similar_code(chroma_db, new_code_content):
    results = chroma_db.similarity_search(new_code_content, k=3)
    return results

# Setup LLM
def setup_llm():
    client = boto3.client('bedrock-runtime', region_name='us-west-2')
    llm = ChatBedrock(
        credentials_profile_name='default',
        model_id='anthropic.claude-3-5-sonnet-20240620-v1:0',
        client=client
    )
    return llm

# Run the code review with multiple contexts
def run_code_review(llm, new_code, contexts):
    template = """
    You are a code review assistant. Use the following reference contexts to review the new code:

    - **Old Codes**: {old_codes}
    - **Google Coding Standards**: {google_coding_standards}
    - **Previous Review Comments**: {review_comments}
    - **Reusable Utilities**: {reusable_utilities}

    Review the new code provided below:
    {new_code}

    For each issue found, provide your feedback in the following format:

    - **File Name**: Name of the file where the issue is located.
    - **Line Number**: Exact line number of the issue.
    - **Issue**: Concisely describe the issue. Use the tone of feedback from "Previous Review Comments" where applicable. 
    - If the issue violates Google coding standards, explicitly state: "As per Google coding standards, this is incorrect."
    - Do not include recommendations or additional explanations. Keep feedback precise and to the point.
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

    sequence = prompt | llm
    review = sequence.invoke(reference_context)
    return review

# Perform the code review
def code_review(new_code_file):
    new_code_content = load_new_code(new_code_file)
    
    # Load contexts from different Chroma DBs
    contexts = {
        "old_codes": query_similar_code(load_chroma_db(old_code_dir), new_code_content),
        "google_coding_standards": query_similar_code(load_chroma_db(coding_standards_dir), new_code_content),
        "review_comments": query_similar_code(load_chroma_db(review_comments_dir), new_code_content),
        "reusable_utilities": query_similar_code(load_chroma_db(reusable_utilities_dir), new_code_content)
    }

    # Setup LLM and run review
    llm = setup_llm()
    review_comments = run_code_review(llm, new_code_content, contexts)
    
    return review_comments

# Example of how the code review would be run
if __name__ == "__main__":
    new_code_file = r"C:\Users\2322191\Downloads\CommonMethods.java"
    review_comments = code_review(new_code_file)
    print(f"Review Comments:\n{review_comments.content}")


