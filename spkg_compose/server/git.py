from spkg_compose.core.parser import read
from spkg_compose.server.api.github import GitHubApi
from spkg_compose.package import SpkgBuild
from spkg_compose.cli.logger import RtLogger

import os


def fetch_git(server, rt_logger: RtLogger):
    for root, _, files in os.walk(server.config.data_dir):
        for file in files:
            if file.endswith('.spkg'):
                file_path = os.path.join(root, file)

                data = read(file_path)
                package = SpkgBuild(data)
                repo_url = package.meta.source

                if repo_url.startswith("https://github.com"):
                    git = GitHubApi(
                        repo_url=repo_url,
                        api_token=server.config.gh_token,
                        server=server,
                        package=package,
                        file_path=file_path,
                    )
                    git.fetch()
