import requests
#from dotenv import Secret
import os
import codecs

def triggerGitAPIPullPRComments():  
    headers = {
        "Accept" : "application/vnd.github+json",
        "X-GitHub-Api-Version" :"2022-11-28",
        "Authorization" : "Bearer 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"
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

        list_pr_comments = []
        pr_data = response.json()

        for item in pr_data: 
            list_pr_comments.append(item["body"]) 
            
        pr_dict = {
            "repoName" : repo,
            "prComments":list_pr_comments
            }
        pr_allrepo_dict.append(pr_dict) 
    return pr_allrepo_dict

#pr_dict = triggerGitAPIPullPRComments()
#print(pr_dict)


def fetchReusableMethodsFromAutomationRepo():
    headers = {
        "Accept" : "application/vnd.github+json",
        "X-GitHub-Api-Version" :"2022-11-28",
        "Authorization" : "Bearer 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"
    }

    githubBaseURL = "https://api.github.com"
    fetchFilesFromADirectory = "/repos/783967/SwagLabsAutomation/contents/src/test/java/swaglabs/common?ref=main"

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

def fetchFilesFromOpenPR():
    headers = {
        "Accept" : "application/vnd.github+json",
        "X-GitHub-Api-Version" :"2022-11-28",
        "Authorization" : "Bearer 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"
    }

    githubBaseURL = "https://api.github.com"
    fetchFilesFromADirectory = "/repos/783967/SwagLabsAutomation/pulls/2/files"

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
fetchReusableMethodsFromAutomationRepo()