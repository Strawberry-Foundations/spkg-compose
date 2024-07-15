from spkg_compose.core.parser import read
from spkg_compose.package import SpkgBuild

import os
import requests


def fetch_git(server):
    for root, _, files in os.walk(server.config.data_dir):
        for file in files:
            if file.endswith('.spkg'):
                file_path = os.path.join(root, file)

                data = read(file_path)
                package = SpkgBuild(data)

                repo_url = package.meta.source

                if repo_url.startswith("https://github.com"):
                    check_for_new_release_or_commit(repo_url)


def check_for_new_release_or_commit(repo_url):
    api_url = convert_to_github_api_url(repo_url, 'releases')
    headers = {'Accept': 'application/vnd.github.v3+json'}
    response = requests.get(api_url, headers=headers)

    if response.status_code == 200:
        releases = response.json()
        if releases:
            latest_release = releases[0]
            print(f"New release found for {repo_url}: {latest_release['tag_name']}")
        else:
            print(f"No releases found for {repo_url}. Checking latest commit.")
            check_latest_commit(repo_url)
    else:
        print(f"Failed to fetch releases for {repo_url}")


def check_latest_commit(repo_url):
    api_url = convert_to_github_api_url(repo_url, 'commits')
    headers = {'Accept': 'application/vnd.github.v3+json'}
    response = requests.get(api_url, headers=headers)

    if response.status_code == 200:
        commits = response.json()
        if commits:
            latest_commit = commits[0]
            print(f"Latest commit for {repo_url}: {latest_commit['sha']}")
    else:
        print(f"Failed to fetch commits for {repo_url}")


def convert_to_github_api_url(repo_url, endpoint):
    parts = repo_url.rstrip('/').split('/')
    owner = parts[-2]
    repo = parts[-1]
    api_url = f"https://api.github.com/repos/{owner}/{repo}/{endpoint}"
    return api_url
