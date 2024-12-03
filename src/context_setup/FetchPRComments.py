import requests
#from dotenv import Secret
import os
import codecs

def triggerGitAPIPullPRComments():  
    pat_token = os.getenv('REPO_ACCESS_TOKEN')
    headers = {
        "Accept" : "application/vnd.github+json",
        "X-GitHub-Api-Version" :"2022-11-28",
        "Authorization" : f"Bearer {pat_token}"
    }

    githubBaseURL = "https://api.github.com"
    fetchAllReposURL = "/users/783967/repos"
    all_repo_details =  requests.get(githubBaseURL + fetchAllReposURL, headers= headers).json()

    list_all_repos =[]
    for item in all_repo_details:
        list_all_repos.append(item["name"])

    pr_allrepo_dict = []
    for repo in list_all_repos:
        githubPullCommentsEndpoint = "/repos/783967/"+repo+"/pulls/comments"
        response = requests.get(githubBaseURL + githubPullCommentsEndpoint, headers= headers)

        pr_data = response.json()
        if len(pr_data) == 0:
            continue

        
        repo_dict = []
        for item in pr_data:
            single_comments ={
                "comment": item["body"],
                "code_snippet": item["diff_hunk"]
            }  
            repo_dict.append(single_comments)
            
        pr_dict = {
            "repoName" : repo,
            "prComments":repo_dict
            }
        pr_allrepo_dict.append(pr_dict) 
    print(pr_allrepo_dict)
    return pr_allrepo_dict

#pr_dict = triggerGitAPIPullPRComments()
#print(pr_dict)


def fetchReusableMethodsFromAutomationRepo():
    pat_token = os.getenv('REPO_ACCESS_TOKEN')
    headers = {
        "Accept" : "application/vnd.github+json",
        "X-GitHub-Api-Version" :"2022-11-28",
        "Authorization" : f"Bearer {pat_token}"
    }

    githubBaseURL = "https://api.github.com"
    fetchFilesFromADirectory = "/repos/783967/SwagLabsAutomation/contents/src/main/java/swaglabs/common?ref=main"

    all_reusable_files =  requests.get(githubBaseURL + fetchFilesFromADirectory, headers= headers).json()

    download_urls = []
    for item in all_reusable_files:
        download_urls.append(item["download_url"])

    all_files = []
    for item in download_urls:
        r = requests.get(item, headers = headers)
        all_files.append(codecs.decode(r.content, 'unicode_escape'))

    for file in all_files:
        print(file)
    
    return all_files

def fetchFilesFromOpenPR(prNumber):
    pat_token = os.getenv('REPO_ACCESS_TOKEN')
    headers = {
        "Accept" : "application/vnd.github+json",
        "X-GitHub-Api-Version" :"2022-11-28",
        "Authorization" : f"Bearer {pat_token}"
    }

    githubBaseURL = "https://api.github.com"
    fetchFilesFromADirectory = f"/repos/783967/SwagLabsAutomation/pulls/{prNumber}/files"

    all_reusable_files =  requests.get(githubBaseURL + fetchFilesFromADirectory, headers= headers).json()
    download_urls = []
    for item in all_reusable_files:
        content_url_data = item["contents_url"]
        if ".log" not in content_url_data and ".html" not in content_url_data:
            content_res = requests.get(item["contents_url"], headers = headers).json()
            print(content_res)
            download_urls.append(content_res["download_url"])

    all_files = []
    for item in download_urls:
        r = requests.get(item, headers= headers)
        all_files.append(codecs.decode(r.content, 'unicode_escape'))

    for file in all_files:
        print(file)
    
    return all_files

def fetchDiffFromPR(prNumber):
    pat_token = os.getenv('REPO_ACCESS_TOKEN')
    headers = {
        "Accept" : "application/vnd.github.v3.diff",
        "X-GitHub-Api-Version" :"2022-11-28",
        "Authorization" : f"Bearer {pat_token}"
    }

    githubBaseURL = "https://api.github.com"
    fetchDiffFromPR = f"/repos/783967/SwagLabsAutomation/pulls/{prNumber}"

    diff_files =  requests.get(githubBaseURL + fetchDiffFromPR, headers= headers).text
    return diff_files