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
            print(content_res)
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
    for item in list:
         if updated_filename in item:
              separator = "@@"
              content_after_separator = fetch_content_after_separator(item, separator)
              line_number = find_line_number(content_after_separator, lineCode)
              #print(line_number)
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
    lines = code_string.split('\n')
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

    pat_token = os.getenv('REPO_ACCESS_TOKEN')
    headers = {
        "Accept" : "application/vnd.github+json",
        "X-GitHub-Api-Version" :"2022-11-28",
        "Authorization" : f"Bearer {pat_token}"
    }
    req_body = {
        "body": "Few review comments",
        "event": "REQUEST_CHANGES",
        "comments": comments
    }
    
    githubBaseURL = "https://api.github.com"
    fetchFilesFromADirectory = f"/repos/783967/SwagLabsAutomation/pulls/{prNumber}/reviews"
    post_review =  requests.post(githubBaseURL + fetchFilesFromADirectory, headers= headers,json=req_body)
    if post_review.status_code ==200:
        return 

def extract_review_comments(review_text):
    # Define the regex patterns to extract file name, line number, and issue
    file_name_pattern = r"- \*\*File Name\*\*: (.+)"
    line_number_pattern = r"- \*\*Line Number\*\*: (\d+)"
    issue_pattern = r"- \*\*Issue\*\*: (.+)"
    
    # Find all matches for each pattern
    file_names = re.findall(file_name_pattern, review_text)
    line_numbers = re.findall(line_number_pattern, review_text)
    issues = re.findall(issue_pattern, review_text)
    
    # Create a list of dictionaries to store the extracted information
    review_comments = []
    for i in range(len(file_names)):
        review_comments.append({
            "file_path": file_names[i],
            "line_number": int(line_numbers[i]),
            "issue": issues[i]
        })
    
    return review_comments
    
write_comments_to_the_pr(4,"""Review Comments:

Based on the provided code and guidelines, here are the issues identified:
 
- **File Name**: CommonMethods.java

- **Line Number**: 1

- **Issue**: Package name should be all lowercase.
 
- **File Name**: CommonMethods.java

- **Line Number**: 16

- **Issue**: Class 'CommonMethods' should be declared as final.
 
- **File Name**: CommonMethods.java

- **Line Number**: 18-19

- **Issue**: Static fields should be declared at the top of the class, before any instance members.
 
- **File Name**: CommonMethods.java

- **Line Number**: 21

- **Issue**: @SuppressWarnings should be used with caution and specific reason should be documented.
 
- **File Name**: CommonMethods.java

- **Line Number**: 47

- **Issue**: Method 'click' uses raw type. As per Google coding standards, this is incorrect.
 
- **File Name**: CommonMethods.java

- **Line Number**: 65

- **Issue**: Method 'waitForElementContainText' uses raw type. As per Google coding standards, this is incorrect.
 
- **File Name**: CommonMethods.java

- **Line Number**: 91

- **Issue**: Method 'addToCartAndVerifyItemAdded' uses raw type. As per Google coding standards, this is incorrect.
 
Based on the provided code and the given instructions, here are the issues identified:
 
- **File Name**: BasePage.java

- **Line Number**: 6

- **Issue**: Unused import: java.io.File.
 
- **File Name**: BasePage.java

- **Line Number**: 41

- **Issue**: As per Google coding standards, this is incorrect. Magic number "//src//test//resources//swaglabs.properties" should be defined as a constant.
 
- **File Name**: BasePage.java

- **Line Number**: 44

- **Issue**: Exception is caught and assertion is made, but the exception is not logged.
 
- **File Name**: BasePage.java

- **Line Number**: 50

- **Issue**: Method throws IOException but doesn't handle it internally.
 
- **File Name**: BasePage.java

- **Line Number**: 53

- **Issue**: As per Google coding standards, this is incorrect. Magic string "//reports//" should be defined as a constant.
 
- **File Name**: BasePage.java

- **Line Number**: 55

- **Issue**: As per Google coding standards, this is incorrect. Duplicated string "//reports//" should be extracted to a constant.
 
Based on the provided code, here are the review comments:
 
- **File Name**: DriverFactory.java

- **Line Number**: 11

- **Issue**: Class should be final as it's not designed for inheritance.
 
- **File Name**: DriverFactory.java

- **Line Number**: 13

- **Issue**: Static field should be final.
 
- **File Name**: DriverFactory.java

- **Line Number**: 14

- **Issue**: Instance field in a utility class.
 
- **File Name**: DriverFactory.java

- **Line Number**: 29

- **Issue**: As per Google coding standards, this is incorrect. Catch blocks should not be empty.
 
- **File Name**: DriverFactory.java

- **Line Number**: 31

- **Issue**: 'else if' branch is unnecessary since 'if' branch always executes.
 
- **File Name**: DriverFactory.java

- **Line Number**: 37

- **Issue**: As per Google coding standards, this is incorrect. Exception variable 'e' is not used in the catch block.
 
- **File Name**: DriverFactory.java

- **Line Number**: 47

- **Issue**: Method should be static as it doesn't use instance members.
 
Here's the code review feedback based on the provided code:
 
- **File Name**: Listeners.java

- **Line Number**: 1

- **Issue**: Package name should be in all lowercase.
 
- **File Name**: Listeners.java

- **Line Number**: 14

- **Issue**: Class 'Listeners' should be in its own file.
 
- **File Name**: Listeners.java

- **Line Number**: 15

- **Issue**: Variable 'driver' should be private.
 
- **File Name**: Listeners.java

- **Line Number**: 18

- **Issue**: Variable 'extentTest' should be private.
 
- **File Name**: Listeners.java

- **Line Number**: 20-23

- **Issue**: Remove TODO comments.
 
- **File Name**: Listeners.java

- **Line Number**: 26-30

- **Issue**: Remove TODO comments.
 
- **File Name**: Listeners.java

- **Line Number**: 33-59

- **Issue**: Method is too long and complex. Consider breaking it down.
 
- **File Name**: Listeners.java

- **Line Number**: 40

- **Issue**: Remove TODO comments.
 
- **File Name**: Listeners.java

- **Line Number**: 51

- **Issue**: Remove TODO comments.
 
- **File Name**: Listeners.java

- **Line Number**: 63-67

- **Issue**: Remove empty method implementations.
 
- **File Name**: Listeners.java

- **Line Number**: 70-74

- **Issue**: Remove empty method implementations.
 
- **File Name**: Listeners.java

- **Line Number**: 77-81

- **Issue**: Remove empty method implementations.
 
- **File Name**: Retry.java

- **Line Number**: 1

- **Issue**: Missing package-info.java file for the package.
 
- **File Name**: Retry.java

- **Line Number**: 10

- **Issue**: Variable 'count' should be declared as private.
 
- **File Name**: Retry.java

- **Line Number**: 11

- **Issue**: Variable 'maxTry' should be declared as private.
 
- **File Name**: Retry.java

- **Line Number**: 14

- **Issue**: Remove TODO comment.
 
- **File Name**: Retry.java

- **Line Number**: 15-20

- **Issue**: As per Google coding standards, this is incorrect. Braces should be used with if, for, and while statements, even when the body is empty or contains only a single statement.
 
- **File Name**: Retry.java

- **Line Number**: 23-24

- **Issue**: Remove unnecessary blank lines at the end of the file.
 
- **File Name**: ExtentReporterNG.java

- **Line Number**: 11

- **Issue**: Method name 'getReportObject' should be in camelCase. As per Google coding standards, this is incorrect.
 
- **File Name**: ExtentReporterNG.java

- **Line Number**: 13

- **Issue**: Missing space around '+' operator.
 
- **File Name**: ExtentReporterNG.java

- **Line Number**: 19

- **Issue**: Variable 'extent' should be declared on a separate line from its initialization.
 
- **File Name**: ExtentReporterNG.java

- **Line Number**: 22-24

- **Issue**: Unnecessary blank lines at the end of the method.
 
- **File Name**: ExtentReporterNG.java

- **Line Number**: 26

- **Issue**: Unnecessary blank line at the end of the file.
 
Based on the provided code and the given instructions, here are the identified issues:
 
- **File Name**: HomePageSteps.java

- **Line Number**: 16

- **Issue**: Instance variables should be private. As per Google coding standards, this is incorrect.
 
- **File Name**: HomePageSteps.java

- **Line Number**: 17

- **Issue**: Logger should be final.
 
- **File Name**: HomePageSteps.java

- **Line Number**: 18

- **Issue**: WebDriver should be final.
 
- **File Name**: HomePageSteps.java

- **Line Number**: 32

- **Issue**: Method is too long. It should be split into smaller, focused methods.
 
- **File Name**: HomePageSteps.java

- **Line Number**: 40

- **Issue**: Variable name 'SwagLabsHomePage' should start with a lowercase letter. As per Google coding standards, this is incorrect.

 
Based on the provided XML content, which appears to be a TestNG test result file, there are no specific code issues to report. This file is automatically generated and contains test execution results rather than actual code. Therefore, there are no coding standard violations or issues to point out in the traditional sense.
 
The XML file shows:

- 2 total tests

- 1 passed test

- 0 failed tests

- 1 ignored test

- Test execution details including timestamps and durations
 
As this is a generated result file, it doesn't require the same type of code review as source code would.
 """)


