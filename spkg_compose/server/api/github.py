from spkg_compose.core.parser import read
from spkg_compose.server.client import BuildServerClient
from spkg_compose.server.yaml import ordered_load, ordered_dump
from spkg_compose.cli.logger import logger, RtLogger
from spkg_compose.utils.colors import *
from spkg_compose.package import SpkgBuild
from enum import Enum

import requests
import json
import copy
import threading
import time


def gh_check_ratelimit(token: str):
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'Authorization': f'Bearer {token}'
    }

    response = requests.get("https://api.github.com/rate_limit", headers=headers)
    result = response.json()
    rlimit_limit = result["resources"]["core"]["limit"]
    rlimit_remaining = result["resources"]["core"]["remaining"]
    rlimit_reset = result["resources"]["core"]["reset"]

    return rlimit_limit, rlimit_remaining, rlimit_reset


class GitReleaseType(Enum):
    COMMIT = 1
    RELEASE = 2


class GitHubApi:
    def __init__(self, repo_url: str, api_token: str, server, package: SpkgBuild, file_path, rt_logger: RtLogger):
        self.status = {}
        self.repo_url = repo_url
        self.repo = ""
        self.api_token = api_token
        self.server = server
        self.package = package
        self.file_path = file_path
        self.rt_logger = rt_logger

        with open(self.server.index, 'r') as json_file:
            self.index = json.load(json_file)

    def fetch(self):
        """Fetches the latest release from GitHub. If there is no release, the last commit is retrieved"""

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

                # If version in index is empty
                if self.index[self.package.meta.id]["latest"] == "":
                    self.rt_logger.info(f"Updating index version for {repo} to {GREEN}{latest_release}{RESET}")
                    self.index[self.package.meta.id]["latest"] = latest_release
                    self.update_json()

                # If version in index matches latest git version
                elif self.index[self.package.meta.id]["latest"] == latest_release:
                    self.rt_logger.info(f"No new release for {repo} ({GREEN}{latest_release}{RESET})")
                    self.update_json()

                # If version in index does not matches latest git version
                else:
                    self.rt_logger.info(f"Release found for {repo}: {CYAN}{latest_release}{RESET}")
                    previous_version = self.index[self.package.meta.id]["latest"]
                    self.index[self.package.meta.id]["latest"] = latest_release
                    self.update(
                        release_type=GitReleaseType.RELEASE,
                        string=latest_release,
                        previous_index_version=previous_version
                    )
            else:
                self.fetch_commit()
        else:
            logger.error(f"Error while fetching {repo} (Status code {response.status_code})")

    def fetch_commit(self):
        """Fetches the latest commit from GitHub."""

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

                # If commit hash in index is empty
                if self.index[self.package.meta.id]["latest"] == "":
                    self.rt_logger.info(f"Updating index version for {repo} to {GREEN}{latest_commit[:7]}{RESET}")
                    self.index[self.package.meta.id]["latest"] = latest_commit
                    self.update_json()

                elif self.index[self.package.meta.id]["latest"] == latest_commit:
                    self.rt_logger.info(f"No new commit for {repo} ({GREEN}{latest_commit[:7]}{RESET})")
                    self.update_json()

                else:
                    self.rt_logger.info(f"Latest commit for {repo}: {CYAN}{latest_commit[:7]}{RESET}")
                    previous_version = self.index[self.package.meta.id]["latest"]
                    self.index[self.package.meta.id]["latest"] = latest_commit
                    self.update(
                        release_type=GitReleaseType.COMMIT,
                        string=latest_commit[:7],
                        previous_index_version=previous_version
                    )
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

    def update(self, release_type: GitReleaseType, string, previous_index_version):
        version = ""
        match release_type:
            case GitReleaseType.COMMIT:
                version = f"git+{string[:7]}"
                if version == self.package.meta.version:
                    logger.info(f"{MAGENTA}routines@git{CRESET}: No update for {self.repo} ({GREEN}{version}{RESET})")
                    self.update_json()
                    return 0
            case GitReleaseType.RELEASE:
                if string.startswith("v"):
                    version = string[1:]
                else:
                    version = string
                if version == self.package.meta.version:
                    logger.info(f"{MAGENTA}routines@git{CRESET}: No update for {self.repo} ({GREEN}{version}{RESET})")
                    self.update_json()
                    return 0
            case _:
                logger.warning(f"{MAGENTA}routines@git{CRESET}: Invalid release type found for {self.repo} ({release_type})")

        logger.info(
            f"{MAGENTA}routines@git{CRESET}: Updating {self.repo} "
            f"({YELLOW}{self.package.meta.version}{RESET}{GRAY}->{GREEN}{version}{RESET})"
        )

        # Check if build server is available
        servers = self.is_buildserver_available(self.index[self.package.meta.id]["architectures"])

        if not servers:
            logger.warning(f"{MAGENTA}routines@git.build{CRESET}: Canceling update process")
            return 0

        self.update_json()

        # Update compose filedata
        with open(self.file_path, 'r') as file:
            content = file.read()

        compose_old = content

        modified_content = content.replace(self.package.meta.version, version)

        with open(self.file_path, 'w') as file:
            file.write(modified_content)

        # Update specfile
        specfile_old = self.update_specfile(version)

        # Update package
        try:
            success = self.update_package(version=version, servers=servers)
        except:
            logger.error(f"{MAGENTA}routines@git.build{CRESET}: Something went wrong while updating package")
            success = False

        successful_processes = 0
        total_processes = len(success)

        for arch, info in success.items():
            if info["status"]:
                successful_processes += 1
                logger.ok(f"{MAGENTA}routines@git.build.{info['name']}{CRESET}: Build succeeded for {CYAN}{arch}{RESET}")
            else:
                logger.warning(
                    f"{MAGENTA}routines@git.build.{info['name']}{CRESET}: Build not succeeded for {CYAN}{arch}{RESET}")
        if successful_processes < total_processes:
            self.rollback(
                compose_old=compose_old,
                specfile_old=specfile_old,
                index_version=previous_index_version,
                release_type=release_type
            )

    def update_specfile(self, version):
        with open(self.index[self.package.meta.id]["specfile"], 'r') as file:
            specfile = ordered_load(file)

        specfile_old = copy.deepcopy(specfile)

        specfile["package"]["version"] = version

        with open(self.index[self.package.meta.id]["specfile"], 'w') as file:
            ordered_dump(specfile, file, default_flow_style=False)

        return specfile_old

    def build_pkg(self, server, arch, package, name):
        _status = server.update_pkg(self, package, name)
        server.disconnect()
        self.status[arch]["status"] = True

    def update_package(self, version, servers):
        self.status = {}
        threads = []

        for arch, info in servers.items():
            name = info["name"]
            logger.info(
                f"{MAGENTA}routines@git.build.{name}{CRESET}: Requesting build process on server '{CYAN}{name}{RESET}' "
                f"for arch '{CYAN}{arch}{RESET}' for package {GREEN}{self.package.meta.id}-{version}{RESET}"
            )

            self.status.update({
                arch: {
                    "name": name,
                    "status": False
                }
            })

            server = BuildServerClient(self.server.config.raw['build_server'][name]["address"])
            server.connect()
            server.auth(
                token=self.server.config.raw['build_server'][name]["token"],
                server_name=name,
            )

            data = read(self.file_path)
            package = SpkgBuild(data)

            thread = threading.Thread(target=self.build_pkg, args=(server, arch, package, name,))
            threads.append(thread)
            thread.start()
            time.sleep(2)

        # for thread in threads:
        #    thread.join()

        return self.status

    def is_buildserver_available(self, architectures):
        servers = {}
        total_available_servers = 0

        if len(architectures) < 2:
            suffix = f"architecture {CYAN}{architectures[0]}{RESET}"
        else:
            suffix = f"architectures {CYAN}{f'{GRAY},{CYAN} '.join(architectures)}{RESET}"

        logger.info(f"{MAGENTA}routines@git.build{CRESET}: Checking whether a build server is available for {suffix}")

        for arch in architectures:
            available_servers = 0

            for name, value in self.server.config.raw['build_server'].items():
                if not value["tags"].__contains__(arch):
                    continue

                server = BuildServerClient(value["address"])
                server.connect()
                server.auth(
                    token=self.server.config.raw['build_server'][name]["token"],
                    server_name=name,
                    silent=True
                )

                status = server.request_slot()
                if status:
                    logger.ok(
                        f"{MAGENTA}routines@git.build{CRESET}: Server '{CYAN}{name}{RESET}' for arch "
                        f"'{GREEN}{arch}{RESET}' is free"
                    )
                    available_servers += 1
                    total_available_servers += 1

                    server.disconnect()
                    servers.update({
                        arch: {
                            "name": name,
                            "available": True
                        }
                    })
                else:
                    logger.warning(
                        f"{MAGENTA}routines@git.build{CRESET}: Server '{CYAN}{name}{RESET}' for arch "
                        f"'{GREEN}{arch}{RESET}' is full"
                    )
                    server.disconnect()
                    servers.update({
                        arch: {
                            "name": name,
                            "available": False
                        }
                    })

            if available_servers == 0:
                logger.warning(
                    f"{MAGENTA}routines@git.build{CRESET}: No build server for arch '{GREEN}{arch}{RESET}' "
                    f"is currently available"
                )

        if total_available_servers == 0:
            logger.warning(
                f"{MAGENTA}routines@git.build{CRESET}: There is currently no build server available for any of "
                f"the available architectures."
            )
            return None

        return servers

    def rollback(self, compose_old, specfile_old, index_version, release_type: GitReleaseType):
        new_version = ""
        old_version = ""
        match release_type:
            case GitReleaseType.RELEASE:
                new_version = self.index[self.package.meta.id]['latest'].replace('v', '')
                old_version = index_version.replace('v', '')
            case GitReleaseType.COMMIT:
                new_version = f"git+{self.index[self.package.meta.id]['latest'][:7]}"
                old_version = f"git+{index_version[:7]}"

        logger.warning(
            f"{MAGENTA}routines@git.build{CRESET}: Something went wrong - Rolling back previous changes "
            f"({GREEN}{new_version}{RESET}{GRAY}->{YELLOW}{old_version}{RESET})"
        )
        with open(self.file_path, 'w') as file:
            file.write(compose_old)

        with open(self.index[self.package.meta.id]["specfile"], 'w') as file:
            ordered_dump(specfile_old, file, default_flow_style=False)

        self.index[self.package.meta.id]["latest"] = index_version
        self.update_json()
