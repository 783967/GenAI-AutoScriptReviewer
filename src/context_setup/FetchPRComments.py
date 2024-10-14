import requests
#from dotenv import Secret
import os
def triggerGitAPIPullPRComments():
    headers = {
        "Accept" : "application/vnd.github+json",
        "X-GitHub-Api-Version" :"2022-11-28",
        "Authorization" : "<Token>"
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
        pr_dict = {"repoName" : repo,
                   "prComments":list_pr_comments
                  }
        pr_allrepo_dict.append(pr_dict) 
    return pr_allrepo_dict

pr_dict = triggerGitAPIPullPRComments()
print(pr_dict)