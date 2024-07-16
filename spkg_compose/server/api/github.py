from spkg_compose.cli.logger import logger
from spkg_compose.utils.colors import *
from spkg_compose.package import SpkgBuild
from enum import Enum

import requests
import json
import yaml


class GitReleaseType(Enum):
    COMMIT = 1
    RELEASE = 2


class GitHubApi:
    def __init__(self, repo_url: str, api_token: str, server, package: SpkgBuild, file_path):
        self.repo_url = repo_url
        self.repo = ""
        self.api_token = api_token
        self.server = server
        self.package = package
        self.file_path = file_path

        with open(self.server.index, 'r') as json_file:
            self.index = json.load(json_file)

    def fetch(self):
        api_url, repo = self.to_gh_api_url("releases")
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {self.api_token}"
        }
        response = requests.get(api_url, headers=headers)

        self.repo = repo

        if response.status_code == 200:
            releases = response.json()
            if releases:
                latest_release = releases[0]["tag_name"]
                if self.index[self.package.meta.id]["latest"] == latest_release:
                    logger.info(f"{MAGENTA}routines@git{CRESET}: No new release for {repo} ({GREEN}{latest_release}{RESET})")
                    return 0

                logger.info(f"{MAGENTA}routines@git{CRESET}: Release found for {repo}: {CYAN}{latest_release}{RESET}")
                self.index[self.package.meta.id]["latest"] = latest_release
                self.update_json()
                self.update_package_files(GitReleaseType.RELEASE, latest_release)
            else:
                self.fetch_commit()
        else:
            logger.error(f"Error while fetching {repo} (Status code {response.status_code})")

    def fetch_commit(self):
        api_url, repo = self.to_gh_api_url("commits")
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {self.api_token}"
        }
        response = requests.get(api_url, headers=headers)

        self.repo = repo

        if response.status_code == 200:
            commits = response.json()
            if commits:
                latest_commit = commits[0]["sha"]
                if self.index[self.package.meta.id]["latest"] == latest_commit:
                    logger.info(f"{MAGENTA}routines@git{CRESET}: No new commit for {repo} ({GREEN}{latest_commit[:7]}{RESET})")
                    return 0

                logger.info(f"{MAGENTA}routines@git{CRESET}: Latest commit for {repo}: {CYAN}{latest_commit[:7]}{RESET}")
                self.index[self.package.meta.id]["latest"] = latest_commit
                self.update_json()
                self.update_package_files(GitReleaseType.COMMIT, latest_commit[:7])
        else:
            logger.error(f"Error while fetching {repo} (Status code {response.status_code})")

    def to_gh_api_url(self, endpoint):
        parts = self.repo_url.rstrip('/').split('/')
        owner = parts[-2]
        repo = parts[-1]
        api_url = f"https://api.github.com/repos/{owner}/{repo}/{endpoint}"
        return api_url, f"{owner}/{repo}"

    def update_json(self):
        with open(self.server.index, 'w') as json_file:
            json.dump(self.index, json_file, indent=2)

    def update_package_files(self, release_type: GitReleaseType, string):
        version = ""
        match release_type:
            case GitReleaseType.COMMIT:
                version = f"git+{string[:7]}"
                if version == self.package.meta.version:
                    logger.info(f"{MAGENTA}routines@git{CRESET}: No update for {self.repo} ({GREEN}{version}{RESET})")
                    return 0
            case GitReleaseType.RELEASE:
                if string.startswith("v"):
                    version = string[1:]
                else:
                    version = string
                if version == self.package.meta.version:
                    logger.info(f"{MAGENTA}routines@git{CRESET}: No update for {self.repo} ({GREEN}{version}{RESET})")
                    return 0
            case _:
                logger.warning(f"{MAGENTA}routines@git{CRESET}: Invalid release type found for {self.repo} ({release_type})")

        logger.info(
            f"{MAGENTA}routines@git{CRESET}: Updating {self.repo} "
            f"({YELLOW}{self.package.meta.version}{RESET}{GRAY}->{GREEN}{version}{RESET})"
        )

        # Update compose file
        with open(self.file_path, 'r') as file:
            content = file.read()

        modified_content = content.replace(self.package.meta.version, version)

        with open(self.file_path, 'w') as file:
            file.write(modified_content)

        # Update specfile
        self.update_specfile(version)

    def update_specfile(self, version):
        with open(self.index[self.package.meta.id]["specfile"], 'r') as file:
            specfile = yaml.safe_load(file)

        specfile["package"]["version"] = version

        with open(self.index[self.package.meta.id]["specfile"], 'w') as file:
            yaml.safe_dump(specfile, file, default_flow_style=False)
