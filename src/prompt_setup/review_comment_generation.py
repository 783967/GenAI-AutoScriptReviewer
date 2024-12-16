import os
from langchain.prompts import PromptTemplate
from langchain_aws import ChatBedrock
from langchain_chroma import Chroma
from langchain.schema import AIMessage
import boto3
from langchain_aws import BedrockEmbeddings
import sys

#pr_number = sys.argv[1]

current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(src_dir)
from write_pr_comments.write_pr_comments_to_git import write_comments_to_the_pr

from context_setup.FetchPRComments import *

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
    client = boto3.client('bedrock-runtime', region_name='us-west-2')
    llm = ChatBedrock(
        credentials_profile_name='default',
        model_id='anthropic.claude-3-5-sonnet-20241022-v2:0',
        client=client,
        model_kwargs={
            "temperature": 0.3,
            "max_tokens" : 10000
        
        }
    )
    return llm

# Run the code review with multiple contexts
def run_code_review(llm, new_code, contexts):
    print('Prompt feed to LLM')
    print('***********New_Code********', str(new_code).encode('utf-8'))
    template = """
    You are a **Java Code Review Assistant** with extensive experience in reviewing automation testing code, focusing on code quality, reusability, adherence to coding standards, and leveraging existing utilities for efficiency. Your expertise spans various testing frameworks, automation libraries, and design patterns in test automation.
 
    Your role is to assist developers by providing **accurate, context-aware review comments**. Use the provided reference contexts to evaluate the new code carefully, and suggest actionable improvements.

    Google Coding Standards you have to refer https://google.github.io/styleguide/javaguide.html  and pull all the information while giving and Standard violation error.

    ***Strictly use  ONLY the google coding style guide -   https://google.github.io/styleguide/javaguide.html .Identify all violation in this style guide. DO NOT USE anything else for code review.*** 
 
    Important point - **Give Minimum 25 Review Comment **

    **Reference Contexts**:
    
    1. **Old Codes**: {old_codes}
    2. **Google Coding Standards**: Refer this link -  {google_coding_standards}
    3. **Previous Review Comments**: {review_comments}
    4. **Reusable Utilities**: {reusable_utilities}
 
    --- 
 
    ### New Code to Review:
    {new_code}
 
    **Review Instructions**:
 
    - For each issue found, provide detailed feedback in the following format:
      - **File Path**: Provide the complete path from the project root to the file where the issue is located.
    - **Line Number**: Specify the exact line number where the issue occurs.And always give a exact number instead of range of line numbers For Example if line which has issue is from 4-6 or 8-12 , you just return the floor value of the range which is 4 and 8 in provided example.
    - Also make sure you follow below guidelines very Strictly to find line number. 
    - The new code provided for review is extracted from **Git diff**, which includes multiple files and their updated snippets.
        - How to Determine the **Line Number**:
        - Each new file starts with a 'diff --git' statement (e.g., 'diff --git a/src/... b/src/...').
        - For every file, use the '@@' syntax to find the starting point of line numbers.
        - If the line starts with '@@ -X,Y +Z,W @@', the line counting starts from 1 from snippet and proceeds line by line until the end of the snippet. 
        - If '--- /dev/null' is present at the beginning of a file, it signifies a newly created file, and the line counting starts from the first line of the snippet and count starts from 1.
        - When a new 'diff --git' is encountered, it marks the start of a new file. Reset the counting for the new file accordingly.
        - Examples:
        - For a file starting with '@@ -19,6 +19,8 @@ @@ public class CommonMethods extends BasePage':
            - The counting begins at line '1' for the updated code snippet and continues sequentially. It means '@@ public class CommonMethods extends BasePage' this line will be number 1
            - If an issue is found on the third line of the snippet, the line number will be '3'.
        - For a newly created file starting with '--- /dev/null' and followed by '@@ -0,0 +1,27 @@':
            - The counting starts from '1', the first line of the snippet.
            - I again repeat *Most Important*, for every file of git diff line number will start from 1. Follow line number from git diff file , don't give line number from original file.
            For Example - You find Voilation in google coding Style on line number 22 in orignal file.But in ### New Code to Review: All files are coming from Git Diff and in Git diff has that same line on line number 5 in code Snippet. So please don't return Line 22 , return line number 5. Please kindly understand this requirement very deeply and thoroughly and provide line number as requested. 

      - **Issue Code ** : Display the exact line of code that has an issue.

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
    - **Issue Code**: Mention the code in that particular line. It should be exactly same line which is present in the git-diff file. Please do not merge or modify the line with other lines
    - **Issue**: Method `validateInput()` duplicates functionality available in the reusable utility `InputValidator.validate()`. 
      Suggested Utility: `src/main/java/com/projectname/utils/InputValidator.java`.
      As per Google coding standards, this is incorrect. Please use the existing utility for consistency and maintainability.
    ```
"""


    prompt = PromptTemplate(
        template=template,
        input_variables=["old_codes", "google_coding_standards", "review_comments", "reusable_utilities", "new_code"]
    )
    '''
    response = requests.get("https://google.github.io/styleguide/javaguide.html",verify=False)
    reference_context = {
        "old_codes": "\n\n".join([doc.page_content for doc in contexts['old_codes']]),
        "google_coding_standards": response.text ,
        "review_comments": "\n\n".join([doc.page_content for doc in contexts['review_comments']]),
        "reusable_utilities": "\n\n".join([doc.page_content for doc in contexts['reusable_utilities']]),
        "new_code": new_code
    }
    
    print("API Response",response.text)
    #print("**Prompt**",template)
    #print('Master Log - All Context', reference_context)
    print('Prompt feed to LLM2')
    sequence = prompt | llm
    print("**Prompt Seq**",prompt)
    #review = sequence.invoke(reference_context)
    print('Prompt feed to LLM3')
    #Format the prompt with actual context
    formatted_prompt = prompt.format( old_codes=reference_context["old_codes"], google_coding_standards=reference_context["google_coding_standards"], review_comments=reference_context["review_comments"], reusable_utilities=reference_context["reusable_utilities"], new_code=reference_context["new_code"] )
    # Print the exact prompt going to the LLM
    print("Exact Prompt Sent to LLM:") 
    #print("------------",formatted_prompt)
    review = llm(formatted_prompt)
    return review
    '''
    response = requests.get("https://google.github.io/styleguide/javaguide.html", verify=False)
    reference_context = {
        "old_codes": "\n\n".join([doc.page_content for doc in contexts['old_codes']]),
        "google_coding_standards": response.text,
        "review_comments": "\n\n".join([doc.page_content for doc in contexts['review_comments']]),
        "reusable_utilities": "\n\n".join([doc.page_content for doc in contexts['reusable_utilities']]),
        "new_code": new_code
    }

    # Format the prompt
    formatted_prompt = prompt.format(
        old_codes=reference_context["old_codes"],
        google_coding_standards=reference_context["google_coding_standards"],
        review_comments=reference_context["review_comments"],
        reusable_utilities=reference_context["reusable_utilities"],
        new_code=reference_context["new_code"]
    )
    
    # Print the exact prompt sent to the LLM
    print("Exact Prompt Sent to LLM:")
    #print(formatted_prompt)
    file_path = r"C:\Users\2322191\Downloads\Prompt_feeded.txt"
    file_path2 = r"C:\Users\2322191\Downloads\Review_comments.txt"
    # Write the content to the file
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(formatted_prompt)

    print(f"Message saved to {file_path}")

    # Feed the formatted prompt to the LLM
    review = llm.invoke(formatted_prompt)
    with open(file_path2, "w", encoding="utf-8") as file:
        file.write(str(review))
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
    new_code_files = fetchDiffFromPR(35)
    '''print('******************** Start New Code ******************************')
    for index, file_content in enumerate(new_code_files, start=1):
        print(f"File {index}: {file_content[:500]}...")  # Display a snippet for each file
    print('******************** End New Code ******************************')'''
    #print(new_code_files)
    # Run the code review for all files
    review_comments = code_review(new_code_files)
    #print(f"Review Comments:\n{str(review_comments).encode('utf-8')}")
    print(f"Review Comments:\n{review_comments}", "Ended")
    write_comments_to_the_pr(35,review_comments)
    print("Method executed successfully")

