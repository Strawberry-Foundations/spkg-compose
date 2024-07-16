from spkg_compose.cli.logger import logger
from spkg_compose.utils.colors import *

import requests


class GitHubApi:
    def __init__(self, repo_url, api_token, server):
        self.repo_url = repo_url
        self.api_token = api_token
        self.server = server

    def fetch(self):
        api_url, repo = self.to_gh_api_url("releases")
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {self.api_token}"
        }
        response = requests.get(api_url, headers=headers)

        if response.status_code == 200:
            releases = response.json()
            if releases:
                latest_release = releases[0]
                logger.info(f"{MAGENTA}routines@git{CRESET}: Release found for {repo}: {latest_release['tag_name']}")
            else:
                self.fetch_commit()
        else:
            logger.error(f"Error while fetching {repo} (Status code {response.status_code})")

    def fetch_commit(self):
        api_url, repo = self.to_gh_api_url("commits")
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'Authorization': f'Bearer {self.api_token}'
        }
        response = requests.get(api_url, headers=headers)

        if response.status_code == 200:
            commits = response.json()
            if commits:
                latest_commit = commits[0]
                logger.info(f"{MAGENTA}routines@git{CRESET}: Latest commit for {repo}: {latest_commit['sha']}")
        else:
            logger.error(f"Error while fetching {repo} (Status code {response.status_code})")

    def to_gh_api_url(self, endpoint):
        parts = self.repo_url.rstrip('/').split('/')
        owner = parts[-2]
        repo = parts[-1]
        api_url = f"https://api.github.com/repos/{owner}/{repo}/{endpoint}"
        return api_url, f"{owner}/{repo}"
