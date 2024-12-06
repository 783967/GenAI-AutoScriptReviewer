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
from write_pr_comments.write_pr_comments_to_git import write_comments_to_the_pr

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
      - **Line Number**: Specify the exact line number where the issue occurs. And always give a exact number instead of range of line numbers For Example if line which has issue is from 14-16 or 118-124 , you just return the floor value of the range which is 14 and 118 in provided example
      - **Issue Description**: 
        - Clearly and concisely describe the issue.
        - If it violates Google coding standards, explicitly state: "As per Google coding standards, this is incorrect."
        - If a reusable utility already exists for a custom method, suggest using the existing utility:
          - Provide the method name and the full file path of the utility.
        - If there is no reusable utility and the method is valid, acknowledge that creating a new method is acceptable.
        - Check **Previous Review Comments** for recurring issues or patterns and validate whether similar issues are present in the new code.
        
 
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
        "old_codes": query_similar_code(load_chroma_db(old_code_dir), new_code_content),
        "google_coding_standards": query_similar_code(load_chroma_db(coding_standards_dir), new_code_content),
        "review_comments": query_similar_code(load_chroma_db(review_comments_dir), new_code_content),
        "reusable_utilities": query_similar_code(load_chroma_db(reusable_utilities_dir), new_code_content),
    }
    
    # Setup LLM and run review for the current file
    llm = setup_llm()
    review_comment = run_code_review(llm, new_code_content, contexts)
    reviews.append(review_comment.content)
    
    return "\n\n".join(reviews)


# Main function
if __name__ == "__main__":
    # Fetch files from PR (returns a list of file contents)
    new_code_files = fetchDiffFromPR(11)
    '''print('******************** Start New Code ******************************')
    for index, file_content in enumerate(new_code_files, start=1):
        print(f"File {index}: {file_content[:500]}...")  # Display a snippet for each file
    print('******************** End New Code ******************************')'''

    print(new_code_files)
    # Run the code review for all files
    review_comments = code_review(new_code_files)
    print(f"Review Comments:\n{review_comments}")
    write_comments_to_the_pr(11,review_comments)
    print("Method executed successfully")

