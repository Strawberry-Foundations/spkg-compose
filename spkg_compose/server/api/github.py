from spkg_compose.core.parser import read
from spkg_compose.server.client import BuildServerClient
from spkg_compose.server.yaml import ordered_load, ordered_dump
from spkg_compose.cli.logger import logger
from spkg_compose.utils.colors import *
from spkg_compose.package import SpkgBuild
from enum import Enum

import requests
import json
import copy
import threading
import time


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

        if success:
            logger.ok(f"{MAGENTA}routines@git.build{CRESET}: Build succeeded")
        else:
            self.rollback(
                compose_old=compose_old,
                specfile_old=specfile_old,
                index_version=previous_index_version
            )

    def update_specfile(self, version):
        with open(self.index[self.package.meta.id]["specfile"], 'r') as file:
            specfile = ordered_load(file)

        specfile_old = copy.deepcopy(specfile)

        specfile["package"]["version"] = version

        with open(self.index[self.package.meta.id]["specfile"], 'w') as file:
            ordered_dump(specfile, file, default_flow_style=False)

        return specfile_old

    def update_package(self, version, servers):
        status = {}
        threads = []

        for arch, info in servers.items():
            name = info["name"]
            logger.info(
                f"{MAGENTA}routines@git.build{CRESET}: Requesting build process on server '{CYAN}{name}{RESET}' "
                f"for arch '{CYAN}{arch}{RESET}' for package {GREEN}{self.package.meta.id}-{version}{RESET}"
            )
            server = BuildServerClient(self.server.config.raw['build_server'][name]["address"])
            server.connect()
            server.auth(
                token=self.server.config.raw['build_server'][name]["token"],
                server_name=name,
            )

            data = read(self.file_path)
            package = SpkgBuild(data)

            def _build():
                _status = server.update_pkg(self, package, name)
                server.disconnect()
                status.update({
                    arch: False
                })

            thread = threading.Thread(target=_build)
            thread.daemon = True
            threads.append(thread)
            thread.start()

            time.sleep(2)

        for thread in threads:
            thread.join()

        return False

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

    def rollback(self, compose_old, specfile_old, index_version):
        logger.warning(
            f"{MAGENTA}routines@git.build{CRESET}: Something went wrong - Rolling back previous changes "
            f"({GREEN}{self.index[self.package.meta.id]['latest'].replace('v', '')}{RESET}{GRAY}->"
            f"{YELLOW}{index_version.replace('v', '')}{RESET})"
        )
        with open(self.file_path, 'w') as file:
            file.write(compose_old)

        with open(self.index[self.package.meta.id]["specfile"], 'w') as file:
            ordered_dump(specfile_old, file, default_flow_style=False)

        self.index[self.package.meta.id]["latest"] = index_version
        self.update_json()
