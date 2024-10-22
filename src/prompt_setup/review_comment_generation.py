import os
from langchain.prompts import PromptTemplate
from langchain_aws import ChatBedrock
from langchain_chroma import Chroma
from langchain.schema import AIMessage
import boto3
from langchain_aws import BedrockEmbeddings

# Get dynamic base directory (root of the project)
ROOT_DIRECTORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
base_persistent_dir = os.path.join(ROOT_DIRECTORY, "src", "vectors")

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
    client = boto3.client('bedrock-runtime', region_name='us-east-1')
    llm = ChatBedrock(
        credentials_profile_name='default',
        model_id='anthropic.claude-3-sonnet-20240229-v1:0',
        client=client
    )
    return llm

# Run the code review with multiple contexts
def run_code_review(llm, new_code, contexts):
    template = """
    You are a code review assistant. Given the following reference contexts:
    
    Old Codes: {old_codes}
    Google Coding Standards: {google_coding_standards}
    Previous Review Comments: {review_comments}
    Reusable Utilities: {reusable_utilities}
    
    Review the following new code:
    {new_code}
    
    Check if the new code follows the provided coding standards, previous reviews, and reference code.
    Provide feedback, comments, and suggestions for improvement.
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
    new_code_file = r"C:\Users\viraj\eclipse-workspace2024AI\SeleniumFrameworkDesign\src\test\java\rahulshettyacademy\tests\StandAloneTest.java"
    review_comments = code_review(new_code_file)
    print(f"Review Comments:\n{review_comments.content}")


