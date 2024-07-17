from spkg_compose.server.git import fetch_git
from spkg_compose.core.parser import read
from spkg_compose.utils.colors import *
from spkg_compose.utils.fmt import calculate_percentage, parse_interval
from spkg_compose.utils.time import unix_to_readable, current_time, convert_time
from spkg_compose.cli.logger import logger
from spkg_compose.package import SpkgBuild

from datetime import datetime

import os
import json
import time
import requests
import yaml


class Running:
    def __init__(self):
        self.indexing = False
        self.gh_checkout = False


rt = Running()


class Routines:
    def __init__(self, server):
        self.server = server
        self.processes = {
            "indexing": self.indexing,
            "git_checkout": self.gh_checkout
        }

    @staticmethod
    def routine(conflicts: bool):
        """-- Routine decorator
            This decorator will wrap some functions that are required for a routine
        """

        def _set_rt(_rt, state: bool):
            match _rt:
                case "gh_checkout":
                    rt.gh_checkout = state
                case "indexing":
                    rt.indexing = state

        def decorator(func):
            def wrapper(self, *args, **kwargs):
                while True:
                    if conflicts:
                        time.sleep(1)
                        continue

                    _set_rt(func.__name__, True)

                    return func(self, *args, **kwargs)

            return wrapper

        return decorator

    @routine(conflicts=rt.gh_checkout)
    def indexing(self):
        """-- Routine for indexing
            This routine checks for new *.spkg files. If there are any new files, this routine will
            append it to the index.json
        """
        i = 0
        logger.info(f"{MAGENTA}routines@indexing{CRESET}: Starting indexing")
        if os.path.exists(self.server.index):
            with open(self.server.index, "r") as json_file:
                index = json.load(json_file)
        else:
            index = {}

        for root, _, files in os.walk(self.server.config.data_dir):
            for file in files:
                if file.endswith(".spkg"):
                    file_path = os.path.join(root, file)

                    data = read(file_path)
                    package = SpkgBuild(data)
                    name = package.meta.id

                    if name not in index:
                        i += 1
                        logger.info(
                            f"{MAGENTA}routines@indexing{CRESET}: Found new compose package '{CYAN}{name}{CRESET}'"
                        )
                        specfile_path = file_path.replace("/compose.spkg", "/specfile.yml")

                        with open(specfile_path, "r") as _config:
                            specfile_data = yaml.load(_config, Loader=yaml.SafeLoader)

                        architectures = []
                        for arch, _ in specfile_data["binpkg"].items():
                            architectures.append(arch)

                        index[name] = {
                            "compose": file_path,
                            "latest": "",
                            "architectures": architectures,
                            "specfile": specfile_path
                        }

        with open(self.server.index, 'w') as json_file:
            json.dump(index, json_file, indent=2)
        if i == 0:
            logger.info(f"{MAGENTA}routines@indexing{CRESET}: Nothing to do, everything up to date.")
        logger.ok(f"{MAGENTA}routines@indexing{CRESET}: Finished indexing, found {i} new packages")

    @routine(conflicts=rt.indexing)
    def gh_checkout(self):
        """-- Routine for git checkout
            This routine checks whether the GitHub repositories of the packages in this repository
            have a new release or a new commit
        """
        logger.info(f"{MAGENTA}routines@git{CRESET}: Starting git fetch")
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'Authorization': f'Bearer {self.server.config.gh_token}'
        }

        response = requests.get("https://api.github.com/rate_limit", headers=headers)
        result = response.json()
        rlimit_limit = result["resources"]["core"]["limit"]
        rlimit_remaining = result["resources"]["core"]["remaining"]
        rlimit_reset = result["resources"]["core"]["reset"]

        logger.info(
            f"{MAGENTA}routines@git{CRESET}: {calculate_percentage(rlimit_limit, rlimit_remaining)}"
            f"of {rlimit_limit} requests available (Will reset on {unix_to_readable(rlimit_reset)})"
        )

        if rlimit_remaining == 0:
            logger.error(f"{MAGENTA}routines@git{CRESET}: API rate limit exceeded. Canceling routine")
            logger.error(
                f"{MAGENTA}routines@git{CRESET}: The API rate limit will be reset on "
                f"{unix_to_readable(rlimit_reset)}"
            )
            return 1

        fetch_git(self)
        logger.info(f"{MAGENTA}routines@git{CRESET}: Finished git fetch")

    def run_routine(self, routine):
        """Runs a routine"""
        process_name = routine['process']
        every = routine['every']
        interval = parse_interval(every)

        next_run = datetime.now()

        while True:
            time_fmt = current_time("%Y-%m-%d %H:%M:%S")
            now = datetime.now()

            if now >= next_run:
                logger.routine(f"Running routine '{CYAN}{routine['name']}{RESET}' at {time_fmt}")

                start_time = time.time()
                self.processes[process_name]()
                end_time = time.time()
                elapsed_time = end_time - start_time

                next_run = now + interval
                next_run_fmt = next_run.strftime("%Y-%m-%d %H:%M:%S")
                logger.routine(
                    f"Routine finished. Took {CYAN}{convert_time(elapsed_time)}{RESET}. "
                    f"Next run for '{CYAN}{routine['name']}{RESET}' at {next_run_fmt}"
                )

            time.sleep(1)