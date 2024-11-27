import os
import requests
import codecs
from context_setup.FetchPRComments import *

def fetchCodeFromFile(fileName):
     pat_token = os.getenv('REPO_ACCESS_TOKEN')
     headers = {
        "Accept" : "application/vnd.github+json",
        "X-GitHub-Api-Version" :"2022-11-28",
        "Authorization" : f"Bearer {pat_token}"
    }
     githubBaseURL = "https://api.github.com"
     fetchFilesFromADirectory = "/repos/783967/SwagLabsAutomation/pulls/4/files"
     all_reusable_files =  requests.get(githubBaseURL + fetchFilesFromADirectory, headers= headers).json()
    
     for item in all_reusable_files:
        content_url_data = item["filename"]
        if fileName in content_url_data:
            content_res = requests.get(item["contents_url"], headers = headers).json()
            print(content_res)
            download_urls = content_res["download_url"]
            break
            
     r = requests.get(download_urls, headers= headers)
     return codecs.decode(r.content, 'unicode_escape')



def splitFilesUsingSeparator(prNumber):
    diff_files = fetchDiffFromPR(prNumber)
    list = diff_files.split("diff --git")
splitFilesUsingSeparator(4)