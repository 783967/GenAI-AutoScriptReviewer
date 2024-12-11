import os
import requests
import codecs
import sys
import re

current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(src_dir)
from context_setup.FetchPRComments import *


def fetchCodeFromFile(fileName,prNumber):
     pat_token = os.getenv('REPO_ACCESS_TOKEN')
     headers = {
        "Accept" : "application/vnd.github+json",
        "X-GitHub-Api-Version" :"2022-11-28",
        "Authorization" : f"Bearer {pat_token}"
    }
     githubBaseURL = "https://api.github.com"
     fetchFilesFromADirectory = f"/repos/783967/SwagLabsAutomation/pulls/{prNumber}/files"
     all_reusable_files =  requests.get(githubBaseURL + fetchFilesFromADirectory, headers= headers,verify= False).json()
    
     for item in all_reusable_files:
        content_url_data = item["filename"]
        if fileName in content_url_data:
            content_res = requests.get(item["contents_url"], headers = headers,verify= False).json()
            #print(content_res)
            download_urls = content_res["download_url"]
            break
            
     r = requests.get(download_urls, headers= headers,verify= False)
     return codecs.decode(r.content, 'unicode_escape')



def splitFilesUsingSeparator(prNumber):
    diff_files = fetchDiffFromPR(prNumber)
    list =[]
    list = diff_files.split("diff --git")
    return list

def fetchRequiredFileDiff(filename, prNumber, lineCode):
    updated_filename = "b/" +filename
    list = splitFilesUsingSeparator(prNumber)
    line_number=0
    for item in list:
         if item == "":
             continue 
        
         if updated_filename in item:
              separator = "@@"
              content_after_separator = fetch_content_after_separator(item, separator)
              line_number = find_line_number(content_after_separator, lineCode)
              #print(line_number)
              return line_number
              #post_pr_comment(prNumber,[{"file_name": "src/test/java/swaglabs/tests/validateHomePageTest.java", "line_number": 6, "issue": "Please add more information here, and fix this typo."}, {"filename": "src/test/java/swaglabs/tests/validateLoginPageTest.java", "line_number": 10, "pr_comment": "Ensure the login button is visible."}])
              break
         
         
    return line_number 
    

def fetch_content_after_separator(content, separator):
    # Find the first occurrence of the separator
    first_index = content.find(separator)  
    if first_index != -1:
        second_index = content.find(separator, first_index + len(separator))
        if second_index != -1:
            return content[second_index + len(separator):]
        else:
            return "Second separator not found in the content."
    else:
        return "First separator not found in the content."
    
def find_line_number(code_string, target_line):
    lines = code_string.strip().split('\n')
    for i, line in enumerate(lines, start=1):
        if target_line.strip() in line.strip():
            return i
    return -1

def write_comments_to_the_pr(prNumber, llmResponse):
    comment_dict_list= extract_review_comments(llmResponse)
    comments =[]
    for comment_dict in comment_dict_list:
        fileName = comment_dict['file_path']
        lineNumber = comment_dict['line_number']
        issue_name = comment_dict['issue']
        fileContent = fetchCodeFromFile(fileName,prNumber)
        lines = fileContent.split('\n')
        line_code = lines[lineNumber-1]
        diff_line_number = fetchRequiredFileDiff(fileName,prNumber,line_code)
        transformed_comments={
             "path": fileName,
             "position": diff_line_number,
             "body": issue_name
        }
        comments.append(transformed_comments)
    print(comments)
    pat_token = os.getenv('REPO_ACCESS_TOKEN')
    headers = {
        "Accept" : "application/vnd.github+json",
        "X-GitHub-Api-Version" :"2022-11-28",
        "Authorization" : f"Bearer {pat_token}"
    }
    req_body = {
        "body": "Few review comments:",
        "event": "REQUEST_CHANGES",
        "comments": comments
    }
    
    githubBaseURL = "https://api.github.com"
    fetchFilesFromADirectory = f"/repos/783967/SwagLabsAutomation/pulls/{prNumber}/reviews"
    post_review =  requests.post(githubBaseURL + fetchFilesFromADirectory, headers= headers,json=req_body)
    print(post_review.status_code)
    if post_review.status_code ==200:
        return 

def extract_review_comments(review_text):
    # Define the regex patterns to extract file name, line number, and issue
    file_name_pattern = r" \*\*File Path\*\*: (.+)"
    line_number_pattern = r" \*\*Line Number\*\*: (\d+)"
    issue_pattern = r"\*\*Issue\*\*:(.*?)(?=\n```|\Z)"
    
    # Find all matches for each pattern
    file_names = re.findall(file_name_pattern, review_text)
    line_numbers = re.findall(line_number_pattern, review_text)
    issues = re.findall(issue_pattern, review_text, re.DOTALL)
    
    # Create a list of dictionaries to store the extracted information
    review_comments = []
    for i in range(len(file_names)):
        review_comments.append({
            "file_path": file_names[i],
            "line_number": int(line_numbers[i]),
            "issue": issues[i].replace("```","")
        })
    print(review_comments)
    return review_comments