from spkg_compose.core.parser import read
from spkg_compose.server.client import BuildServerClient
from spkg_compose.server.yaml import ordered_load, ordered_dump
from spkg_compose.cli.logger import RtLogger
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

    def update_json(self):
        with open(self.server.index, 'w') as json_file:
            json.dump(self.index, json_file, indent=2)

    def to_gh_api_url(self, endpoint):
        parts = self.repo_url.rstrip('/').split('/')
        owner = parts[-2]
        repo = parts[-1]
        api_url = f"https://api.github.com/repos/{owner}/{repo}/{endpoint}"
        return api_url, f"{owner}/{repo}"

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

                for arch, up_to_date in self.index[self.package.meta.id]["architectures"].items():
                    if not up_to_date:
                        self.rt_logger.warning(
                            f"Package '{CYAN}{self.package.meta.id}{RESET}' for arch '{GREEN}{arch}{RESET}' "
                            f"was not updated correctly during the last update"
                        )

                        self.pre_update_single_arch(arch=arch, release_type=GitReleaseType.RELEASE)

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
                    self.rt_logger.info(f"New release found for {repo}: {CYAN}{latest_release}{RESET}")
                    previous_version = self.index[self.package.meta.id]["latest"]
                    self.index[self.package.meta.id]["latest"] = latest_release
                    status = self.pre_update(
                        release_type=GitReleaseType.RELEASE,
                        string=latest_release,
                        previous_index_version=previous_version
                    )

                    match status:
                        case 255:
                            self.rt_logger.warning(
                                f"The index has a different version than the compose file "
                                f"(compose: {GREEN}{self.package.meta.version}{RESET}, "
                                f"index: {YELLOW}{previous_version.replace('v', '')}{RESET})"
                            )
                            self.rt_logger.warning(
                                "This should not happen. Either the version was changed manually or the "
                                "update process was interrupted."
                            )
            else:
                self.fetch_commit()
        else:
            self.rt_logger.error(f"Error while fetching {repo} (Status code {response.status_code})")

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

                for arch, up_to_date in self.index[self.package.meta.id]["architectures"].items():
                    if not up_to_date:
                        self.rt_logger.warning(
                            f"Package '{CYAN}{self.package.meta.id}{RESET}' for arch '{GREEN}{arch}{RESET}' "
                            f"was not updated correctly during the last update"
                        )

                        self.pre_update_single_arch(arch=arch, release_type=GitReleaseType.COMMIT)

                # If commit hash in index is empty
                if self.index[self.package.meta.id]["latest"] == "":
                    self.rt_logger.info(f"Updating index version for {repo} to {GREEN}{latest_commit[:7]}{RESET}")
                    self.index[self.package.meta.id]["latest"] = latest_commit
                    self.update_json()

                elif self.index[self.package.meta.id]["latest"] == latest_commit:
                    self.rt_logger.info(f"No new commit for {repo} ({GREEN}{latest_commit[:7]}{RESET})")
                    self.update_json()

                else:
                    self.rt_logger.info(f"New commit found for {repo}: {CYAN}{latest_commit[:7]}{RESET}")
                    previous_version = self.index[self.package.meta.id]["latest"]
                    self.index[self.package.meta.id]["latest"] = latest_commit
                    status = self.pre_update(
                        release_type=GitReleaseType.COMMIT,
                        string=latest_commit[:7],
                        previous_index_version=previous_version
                    )

                    match status:
                        case 255:
                            self.rt_logger.warning(
                                f"The index has a different version than the compose file "
                                f"(compose: {GREEN}{self.package.meta.version[4:]}{RESET}, "
                                f"index: {YELLOW}{previous_version[:7]}{RESET})"
                            )
                            self.rt_logger.warning(
                                "This should not happen. Either the version was changed manually or the "
                                "update process was interrupted."
                            )
        else:
            self.rt_logger.error(f"Error while fetching {repo} (Status code {response.status_code})")

    def pre_update(self, release_type: GitReleaseType, string, previous_index_version):
        version = ""
        match release_type:
            case GitReleaseType.COMMIT:
                version = f"git+{string[:7]}"
                if version == self.package.meta.version:
                    self.rt_logger.info(f"No update for {self.repo} ({GREEN}{version}{RESET})")
                    self.update_json()
                    return 255

            case GitReleaseType.RELEASE:
                if string.startswith("v"):
                    version = string[1:]
                else:
                    version = string
                if version == self.package.meta.version:
                    self.rt_logger.info(f"No update for {self.repo} ({GREEN}{version}{RESET})")
                    self.update_json()
                    return 255
            case _:
                self.rt_logger.warning(f"Invalid release type found for {self.repo} ({release_type})")

        self.rt_logger.info(
            f"Updating {self.repo} ({YELLOW}{self.package.meta.version}{RESET}{GRAY}->{GREEN}{version}{RESET})"
        )

        # Check if build server is available
        servers = self.is_buildserver_available(self.index[self.package.meta.id]["architectures"])

        if not servers:
            self.rt_logger.warning("Canceling update process", suffix="build")
            return 2

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
            self.rt_logger.error("Something went wrong while updating package", suffix="build")
            success = False

        successful_processes = 0
        total_processes = len(success)

        # todo: write if package update was successful for every arch in index.json
        for arch, info in success.items():
            if info["status"]:
                successful_processes += 1
                self.rt_logger.ok(f"Build succeeded for {CYAN}{arch}{RESET}", suffix=f"build.{info['name']}")
            else:
                self.rt_logger.warning(
                    f"Build not succeeded for {CYAN}{arch}{RESET}", suffix=f"build.{info['name']}"
                )
                self.index[self.package.meta.id]["architectures"][arch] = False
                self.update_json()

        if successful_processes < total_processes:
            self.rollback(
                compose_old=compose_old,
                specfile_old=specfile_old,
                index_version=previous_index_version,
                release_type=release_type
            )

    def pre_update_single_arch(self, arch: str, release_type: GitReleaseType):
        string = self.index[self.package.meta.id]["latest"]
        version = ""
        match release_type:
            case GitReleaseType.COMMIT:
                version = f"git+{string[:7]}"

            case GitReleaseType.RELEASE:
                if string.startswith("v"):
                    version = string[1:]
                else:
                    version = string

        self.rt_logger.info(
            f"Updating {self.repo} for arch '{GREEN}{arch}{RESET}' "
            f"({YELLOW}{self.package.meta.version}{RESET}{GRAY}->{GREEN}{version}{RESET})"
        )

        # Check if build server is available
        servers = self.is_buildserver_available({arch: False})

        if not servers:
            self.rt_logger.warning(f"Canceling update process", suffix="build")
            return 2

        # START FROM HERE
        # Update package
        try:
            success = self.update_package_single_arch(version=version, servers=servers)
        except:
            self.rt_logger.error(f"Something went wrong while updating package" , suffix="build")
            success = False

        # todo: write if package update was successful for every arch in index.json
        for arch, info in success.items():
            if info["status"]:
                self.rt_logger.ok(f"Build succeeded for {CYAN}{arch}{RESET}", suffix=f"build.{info['name']}")
                self.index[self.package.meta.id]["architectures"][arch] = True
                self.update_json()
            else:
                self.rt_logger.warning(
                    message=f"Build not succeeded for {CYAN}{arch}{RESET}",
                    suffix=f"build.{info['name']}"
                )
                self.index[self.package.meta.id]["architectures"][arch] = False
                self.update_json()

    def update_specfile(self, version):
        with open(self.index[self.package.meta.id]["specfile"], 'r') as file:
            specfile = ordered_load(file)

        specfile_old = copy.deepcopy(specfile)

        specfile["package"]["version"] = version

        with open(self.index[self.package.meta.id]["specfile"], 'w') as file:
            ordered_dump(specfile, file, default_flow_style=False)

        return specfile_old

    def build_pkg(self, server, arch, package, name):
        _status = server.update_pkg(self, package, name, self.server.config.repo_api_url)
        server.disconnect()
        self.status[arch]["status"] = True

    def update_package(self, version, servers):
        self.status = {}
        threads = []

        for arch, info in servers.items():
            name = info["name"]
            self.rt_logger.info(
                f"Requesting build process on server '{CYAN}{name}{RESET}' for arch '{CYAN}{arch}{RESET}' for "
                f"package {GREEN}{self.package.meta.id}-{version}{RESET}", suffix=f"build.{name}"
            )

            self.status.update({
                arch: {
                    "name": name,
                    "status": False
                }
            })

            server = BuildServerClient(self.server.config.raw['build_server'][name]["address"], self.rt_logger)
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
            time.sleep(1)

        for thread in threads:
            thread.join()

        return self.status

    def update_package_single_arch(self, version, servers):
        self.status = {}

        for arch, info in servers.items():
            name = info["name"]
            self.rt_logger.info(
                f"Requesting build process on server '{CYAN}{name}{RESET}' for arch '{CYAN}{arch}{RESET}' for "
                f"package {GREEN}{self.package.meta.id}-{version}{RESET}", suffix=f"build.{name}"
            )

            self.status.update({
                arch: {
                    "name": name,
                    "status": False
                }
            })

            server = BuildServerClient(self.server.config.raw['build_server'][name]["address"], self.rt_logger)
            server.connect()
            server.auth(
                token=self.server.config.raw['build_server'][name]["token"],
                server_name=name,
            )

            data = read(self.file_path)
            package = SpkgBuild(data)

            _status = server.update_pkg(self, package, name, self.server.config.repo_api_url)
            server.disconnect()
            self.status[arch]["status"] = True

        return self.status

    def is_buildserver_available(self, architectures):
        servers = {}
        total_available_servers = 0

        archs = list(architectures.keys())

        if len(archs) < 2:
            suffix = f"architecture {CYAN}{archs[0]}{RESET}"
        else:
            suffix = f"architectures {CYAN}{f'{GRAY},{CYAN} '.join(archs)}{RESET}"

        self.rt_logger.info(f"Checking whether a build server is available for {suffix}", suffix="build")

        for arch in architectures:
            available_servers = 0

            for name, value in self.server.config.raw['build_server'].items():
                if not value["tags"].__contains__(arch):
                    continue

                server = BuildServerClient(value["address"], self.rt_logger)
                server.connect()
                server.auth(
                    token=self.server.config.raw['build_server'][name]["token"],
                    server_name=name,
                    silent=True
                )

                status = server.request_slot()
                if status:
                    self.rt_logger.ok(
                        f"Server '{CYAN}{name}{RESET}' for arch '{GREEN}{arch}{RESET}' is free", suffix="build"
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
                    self.rt_logger.warning(
                        f"Server '{CYAN}{name}{RESET}' for arch '{GREEN}{arch}{RESET}' is full", suffix="build"
                    )
                    server.disconnect()
                    servers.update({
                        arch: {
                            "name": name,
                            "available": False
                        }
                    })

            if available_servers == 0:
                self.rt_logger.warning(
                    f"No build server for arch '{GREEN}{arch}{RESET}' is currently available", suffix="build"
                )
                with open(self.server.index, 'r') as json_file:
                    index = json.load(json_file)

                with open(self.server.index, 'w') as json_file:
                    index[self.package.meta.id]["architectures"][arch] = False
                    self.index[self.package.meta.id]["architectures"][arch] = False
                    json.dump(index, json_file, indent=2)

        if total_available_servers == 0:
            self.rt_logger.warning(
                f"There is currently no build server available for any of the available architectures.", suffix="build"
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

        self.rt_logger.warning(
            f"Something went wrong - Rolling back previous changes "
            f"({GREEN}{new_version}{RESET}{GRAY}->{YELLOW}{old_version}{RESET})", suffix="build"
        )
        with open(self.file_path, 'w') as file:
            file.write(compose_old)

        with open(self.index[self.package.meta.id]["specfile"], 'w') as file:
            ordered_dump(specfile_old, file, default_flow_style=False)

        self.index[self.package.meta.id]["latest"] = index_version
        self.update_json()
