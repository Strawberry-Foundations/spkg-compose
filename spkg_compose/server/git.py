from spkg_compose.core.parser import read
from spkg_compose.package import SpkgBuild
from spkg_compose.cli.logger import logger
from spkg_compose.server.config import config
from spkg_compose.utils.colors import *

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
    api_url, repo = convert_to_github_api_url(repo_url, 'releases')
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'Authorization': f'Bearer {config.gh_token}'
    }
    response = requests.get(api_url, headers=headers)

    if response.status_code == 200:
        releases = response.json()
        if releases:
            latest_release = releases[0]
            logger.info(f"{MAGENTA}routines@fetch_git{CRESET}: Release found for {repo}: {latest_release['tag_name']}")
        else:
            check_latest_commit(repo_url)
    else:
        logger.error(f"Error while fetching {repo} (Status code {response.status_code})")


def check_latest_commit(repo_url):
    api_url, repo = convert_to_github_api_url(repo_url, 'commits')
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'Authorization': f'Bearer {config.gh_token}'
    }
    response = requests.get(api_url, headers=headers)

    if response.status_code == 200:
        commits = response.json()
        if commits:
            latest_commit = commits[0]
            logger.info(f"{MAGENTA}routines@fetch_git{CRESET}: Latest commit for {repo}: {latest_commit['sha']}")
    else:
        logger.error(f"Error while fetching {repo} (Status code {response.status_code})")


def convert_to_github_api_url(repo_url, endpoint):
    parts = repo_url.rstrip('/').split('/')
    owner = parts[-2]
    repo = parts[-1]
    api_url = f"https://api.github.com/repos/{owner}/{repo}/{endpoint}"
    return api_url, f"{owner}/{repo}"
