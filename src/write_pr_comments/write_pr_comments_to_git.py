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

def fetchRequiredFileDiff(filename, prNumber,lineNumber, lineCode):
    updated_filename = filename
    list = splitFilesUsingSeparator(prNumber)
    line_number=0
    for item in list:
         if item == "":
             continue 
        
         if updated_filename in item:
              separator = "@@"
              content_after_separator = fetch_content_after_separator(item, separator)
              content_after_separator = content_after_separator.encode('latin1').decode('utf-8')
              line_number = find_line_number(content_after_separator, lineNumber,lineCode)
              if line_number==-1:
                  line_number = find_line_number_entire_file(content_after_separator,lineNumber,lineCode)
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
    
def find_line_number(code_string, target_line_number,target_line):
    lines = code_string.strip().split('\n')
    if target_line_number-10>0:

        start=target_line_number-10
    else:
        start=1

    if (target_line_number+10)<(len(lines)-1):
        end=target_line_number+10
    else:
        end=(len(lines)-1)
    
    for i, line in enumerate(lines[start:end], start=start):
        if target_line.strip() in line.strip():
            if code_string[0]=='\n':
                i=i+1
            return i
    return -1

def write_comments_to_the_pr(prNumber, llmResponse):
    comment_dict_list= extract_review_comments(llmResponse)
    comments =[]
    for comment_dict in comment_dict_list:
        fileName = comment_dict['file_path']
        lineNumber = comment_dict['line_number']
        issue_name = comment_dict['issue']
        line_code = comment_dict['line_code']
        #fileContent = fetchCodeFromFile(fileName,prNumber)
        #lines = fileContent.split('\n')
        #line_code = lines[lineNumber-1]
        diff_line_number = fetchRequiredFileDiff(fileName,prNumber,lineNumber,line_code)
        transformed_comments={
             "path": fileName,
             "position": diff_line_number,
             "body": issue_name
        }
        comments.append(transformed_comments)
    print(str(comments).encode('utf-8'))
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
    print(str(post_review.status_code).encode('utf-8'))
    if post_review.status_code ==200:
        return 

def extract_review_comments(review_text):
    # Define the regex patterns to extract file name, line number, and issue
    file_name_pattern = r" \*\*File Path\*\*: (.+)"
    line_number_pattern = r" \*\*Line Number\*\*: (\d+)"
    line_dode_pattern = r" \*\*Issue Code\*\*: (.+)"
    issue_pattern = r'- \*\*Issue\*\*: (.+)'
    
    # Find all matches for each pattern
    file_names = re.findall(file_name_pattern, review_text)
    line_numbers = re.findall(line_number_pattern, review_text)
    issues = re.findall(issue_pattern, review_text)
    issues = re.findall(issue_pattern, review_text)
    line_code = re.findall(line_dode_pattern,review_text)
    
    for i in range(len(issues)):
        print('issues[',i ,']=',issues[i])
    print('line_code = ', str(line_code).encode('utf-8'))
    print("Length of filename:",len(file_names))
    print("Lenght of Issue:",len(issues))
    print("Lenght of Line code:",len(line_code))
    # Create a list of dictionaries to store the extracted information
    review_comments = []
    for i in range(len(file_names)):
        try:
            print("Inside Try i= :", i)
            file_path = file_names[i]
            #print('After File Path For i =' , i)
            line_number = int(line_numbers[i])
            #print('After Line Number For i =' , i)
            issue = issues[i]
            #print('After Issue For i =' , i)
            line_codes =  line_code[i]
            #print('After Line Code For i =' , i)
            jsonres = {
                "file_path": file_path,
                "line_number": line_number,
                "issue": issue,
                "line_code": line_codes
                }
            print(jsonres)
            review_comments.append(jsonres)
        except Exception as e:
            print("Exception occured for i =:",i,"Exeception message: ",{str(e)})
    #print(str(review_comments).encode('utf-8'))
    return review_comments

def find_line_number_entire_file(code_string,target_line_number, target_line):
    lines = code_string.strip().split('\n')
    for i, line in enumerate(lines, start=1):
        if target_line.strip() in line.strip():
            if code_string[0]=='\n':
                i=i+1
            return i
    return target_line_number

#write_comments_to_the_pr(51,"""I\'ll review the code according to Google Java Style Guide and provide all violations in a single response:\n\n```\n1. **File Path**: src/test/java/swaglabs/TestSwaglabs/testJava.java\n- **Line Number**: 4\n- **Issue Code**: String XMLHTTPRequest="";\n- **Issue**: As per Google coding standards, this is incorrect. Variable name should be \'xmlHttpRequest\' in camelCase.\n\n2. **File Path**: src/test/java/swaglabs/TestSwaglabs/testJava.java\n- **Line Number**: 5\n- **Issue Code**: String newCustomerID = "";\n- **Issue**: As per Google coding standards, this is incorrect. Variable name should be \'newCustomerId\' in camelCase.\n\n3. **File Path**: src/test/java/swaglabs/TestSwaglabs/testJava.java\n- **Line Number**: 7\n- **Issue Code**: int turnOn2Sv=0;\n- **Issue**: As per Google coding standards, this is incorrect. Missing space around \'=\' operator.\n\n4. **File Path**: src/test/java/swaglabs/tests/ui/GOOGLECODE_VIOLATE/VALIDATE_Google_Standard_Violation_12s.java\n- **Line Number**: 20\n- **Issue Code**: private int         x;\n- **Issue**: As per Google coding standards, this is incorrect. Excessive whitespace after variable type.\n\n5. **File Path**: src/test/java/swaglabs/tests/ui/GOOGLECODE_VIOLATE/VALIDATE_Google_Standard_Violation_12s.java\n- **Line Number**: 21\n- **Issue Code**: int a, b,   c,  d;\n- **Issue**: As per Google coding standards, this is incorrect. Multiple variable declarations in one line and inconsistent spacing.\n\n6. **File Path**: src/test/java/swaglabs/tests/ui/GOOGLECODE_VIOLATE/VALIDATE_Google_Standard_Violation_12s.java\n- **Line Number**: 22\n- **Issue Code**: String[][] u = {  {"foo"}   };\n- **Issue**: As per Google coding standards, this is incorrect. Excessive whitespace in array initialization.\n\n7. **File Path**: src/test/java/swaglabs/tests/ui/GOOGLECODE_VIOLATE/VALIDATE_Google_Standard_Violation_12s.java\n- **Line Number**: 23\n- **Issue Code**: static public final String va = null;\n- **Issue**: As per Google coding standards, this is incorrect. Modifier order should be \'public static final\'.\n\n8. **File Path**: src/test/java/swaglabs/tests/ui/GOOGLECODE_VIOLATE/VALIDATE_Google_Standard_Violation_12s.java\n- **Line Number**: 24\n- **Issue Code**: Long l = 43543543l;\n- **Issue**: As per Google coding standards, this is incorrect. Long suffix should be uppercase \'L\'.\n\n9. **File Path**: src/test/java/swaglabs/tests/ui/GOOGLECODE_VIOLATE/VALIDATE_Google_Standard_Violation_12s.java\n- **Line Number**: 25\n- **Issue Code**: static final ImmutableList<String> immutaBLE = ImmutableList.of("Ed", "Ann");\n- **Issue**: As per Google coding standards, this is incorrect. Constant name should be in UPPER_SNAKE_CASE.\n\n10. **File Path**: src/test/java/swaglabs/tests/ui/GOOGLECODE_VIOLATE/VALIDATE_Google_Standard_Violation_12s.java\n- **Line Number**: 26\n- **Issue Code**: String Non__cOnstant;\n- **Issue**: As per Google coding standards, this is incorrect. Variable name should be in camelCase without underscores.\n\n11. **File Path**: src/test/java/swaglabs/tests/ui/GOOGLECODE_VIOLATE/VALIDATE_Google_Standard_Violation_12s.java\n- **Line Number**: 33\n- **Issue Code**: public void valiTheSwagLabsByLoginIntoItAndThenValidateUserIsSuccessfullyLandedIntoItAfterThatLogoutFromApplication(){\n- **Issue**: As per Google coding standards, this is incorrect. Method name is too long and missing space before opening brace.\n\n12. **File Path**: src/test/java/swaglabs/tests/ui/GOOGLECODE_VIOLATE/VALIDATE_Google_Standard_Violation_12s.java\n- **Line Number**: 41\n- **Issue Code**: if(1>0)\n- **Issue**: As per Google coding standards, this is incorrect. Missing spaces around operator \'>\' and missing braces for if statement.\n\n13. **File Path**: src/test/java/swaglabs/tests/ui/GOOGLECODE_VIOLATE/VALIDATE_Google_Standard_Violation_12s.java\n- **Line Number**: 46\n- **Issue Code**: } catch (Exception e) {}\n- **Issue**: As per Google coding standards, this is incorrect. Empty catch block without comment explaining why exception is ignored.\n\n14. **File Path**: src/test/java/swaglabs/tests/ui/GOOGLECODE_VIOLATE/VALIDATE_Google_Standard_Violation_12s.java\n- **Line Number**: 47\n- **Issue Code**: new CommonMethods().click(null); new CommonMethods().launchUrl(null);\n- **Issue**: As per Google coding standards, this is incorrect. Multiple statements on same line.\n\n15. **File Path**: src/test/java/swaglabs/tests/ui/GOOGLECODE_VIOLATE/VALIDATE_Google_Standard_Violation_12s.java\n- **Line Number**: 51\n- **Issue Code**: @Deprecated\t@NotNull @Override public String toString() {return null;};\n- **Issue**: As per Google coding standards, this is incorrect. Each annotation should be on its own line and missing space after method.\n\n16. **File Path**: src/test/java/swaglabs/tests/ui/FrameworkStandardViolationTest.java\n- **Line Number**: 16\n- **Issue Code**: @Test(description = "validate")\n- **Issue**: As per Google coding standards, this is incorrect. Test description is not descriptive enough.\n\n17. **File Path**: src/test/java/swaglabs/tests/ui/FrameworkStandardViolationTest.java\n- **Line Number**: 43\n- **Issue Code**: Thread.sleep(100);\n- **Issue**: As per Google coding standards, this is incorrect. Avoid using Thread.sleep in tests.\n\n18. **File Path**: src/main/java/swaglabs/pageobjects/SwagLabsHomePage.java\n- **Line Number**: 26\n- **Issue Code**: @FindBy(css=".app_logo")\n- **Issue**: As per Google coding standards, this is incorrect. Missing space after \'css=\'.\n\n19. **File Path**: src/main/java/swaglabs/pageobjects/LoginPage.java\n- **Line Number**: 23\n- **Issue Code**: public WebElement userName;\n- **Issue**: As per Google coding standards, this is incorrect. Public field should be private with getter/setter.\n\n20. **File Path**: src/main/java/swaglabs/pageobjects/LoginPage.java\n- **Line Number**: 26\n- **Issue Code**: public WebElement passWord;\n- **Issue**: As per Google coding standards, this is incorrect. Public field should be private with getter/setter.\n\n21. **File Path**: src/main/java/swaglabs/common/CommonMethods.java\n- **Line Number**: 96\n- **Issue Code**: if (!swagLabsHomePage.getValueFromEmptyCartBadge().isEmpty())\n- **Issue**: As per Google coding standards, this is incorrect. Missing braces for if statement block.\n\n22. **File Path**: src/main/java/swaglabs/components/BasePage.java\n- **Line Number**: 47\n- **Issue Code**: /** Get SCreenshot * @param testCaseName * @param driver\t * @return\t * @throws IOException\t */\n- **Issue**: As per Google coding standards, this is incorrect. Javadoc formatting is incorrect and contains typo in \'Screenshot\'.\n\n23. **File Path**: src/test/java/swaglabs/tests/ui/GOOGLECODE_VIOLATE/VALIDATE_Google_Standard_Violation_12s.java\n- **Line Number**: 35\n- **Issue Code**: switch (1) {\n- **Issue**: As per Google coding standards, this is incorrect. Switch statement missing default case.\n\n24. **File Path**: src/test/java/swaglabs/tests/ui/GOOGLECODE_VIOLATE/VALIDATE_Google_Standard_Violation_12s.java\n- **Line Number**: 54\n- **Issue Code**: return null;};\n- **Issue**: As per Google coding standards, this is incorrect. Extra semicolon after method closing brace.\n\n25. **File Path**: src/test/java/swaglabs/tests/ui/GOOGLECODE_VIOLATE/VALIDATE_Google_Standard_Violation_12s.java\n- **Line Number**: 1\n- **Issue Code**: package swaglabs.tests.ui.GOOGLECODE_VIOLATE;\n- **Issue**: As per Google coding standards, this is incorrect. Package name should be all lowercase without underscores.\n```""")
