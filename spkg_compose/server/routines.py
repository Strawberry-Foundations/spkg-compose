from spkg_compose import init_dir
from spkg_compose.server.api.github import gh_check_ratelimit
from spkg_compose.server.git import fetch_git
from spkg_compose.server.config import config as _cfg
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
import yaml


class Running:
    def __init__(self):
        self.indexing = False
        self.gh_checkout = False


rt = Running()


class Routines:
    def __init__(self, server):
        self.server = server
        self.config = _cfg
        self.index = f"{init_dir}/data/index.json"

        self.processes = {
            "indexing": self.indexing,
            "checkout": self.checkout
        }

    @staticmethod
    def routine(conflicts: str = None):
        """-- Routine decorator
            This decorator will wrap some functions that are required for a routine
        """

        def _get_rt(_conflicts):
            match _conflicts:
                case "checkout":
                    return rt.gh_checkout
                case "indexing":
                    return rt.indexing

        def _set_rt(_rt, state: bool):
            match _rt:
                case "checkout":
                    rt.gh_checkout = state
                case "indexing":
                    rt.indexing = state

        def decorator(func):
            def wrapper(self, *args, **kwargs):
                _set_rt(func.__name__, True)

                if conflicts is not None:
                    if _get_rt(conflicts):
                        logger.routine(
                            f"{MAGENTA}{func.__name__}{RESET}: Waiting for routine '{CYAN}{conflicts}{RESET}' to finish"
                        )

                while True:
                    if conflicts is not None:
                        if _get_rt(conflicts):
                            time.sleep(1)
                            continue

                    rt_logger = RtLogger(rt_name=func.__name__)

                    function = func(self, rt_logger, *args, **kwargs)

                    _set_rt(func.__name__, False)

                    return function

            return wrapper

        return decorator

    @routine(conflicts="gh_checkout")
    def indexing(self, rt_logger: RtLogger):
        """-- Routine for indexing
            This routine checks for new *.spkg files. If there are any new files, this routine will
            append it to the index.json
        """
        i = 0

        rt_logger.info("Starting indexing")

        # Check if index path already exists and load index, if not, create new index
        if os.path.exists(self.server.index):
            with open(self.server.index, "r") as json_file:
                index = json.load(json_file)
        else:
            index = {}

        # Iterate data dir for *.spkg files
        for root, _, files in os.walk(self.server.config.data_dir):
            for file in files:
                if file.endswith(".spkg"):
                    file_path = os.path.join(root, file)

                    data = read(file_path)
                    package = SpkgBuild(data)
                    name = package.meta.id

                    # If cached data is not in index, add data to index.json
                    if name not in index:
                        i += 1
                        rt_logger.info(f"Found new compose package '{CYAN}{name}{CRESET}'")
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
            rt_logger.info(f"Nothing to do, everything up to date.")

        rt_logger.ok(f"Finished indexing, found {i} new packages")

    @routine(conflicts="indexing")
    def checkout(self, rt_logger: RtLogger):
        """-- Routine for git checkout
            This routine checks whether the GitHub repositories of the packages in this repository
            have a new release or a new commit
        """
        rt_logger.info(f"Starting checkout")

        limit, remaining, reset = gh_check_ratelimit(self.server.config.gh_token)

        rt_logger.info(
            f"{calculate_percentage(limit, remaining)} of {limit} requests available "
            f"(Will reset on {unix_to_readable(reset)})"
        )

        if remaining == 0:
            rt_logger.error(f"API rate limit exceeded. Canceling routine")
            rt_logger.error(f"The API rate limit will be reset on {unix_to_readable(reset)}")
            return 1

        fetch_git(self, rt_logger)
        rt_logger.ok(f"Finished checkout")

    def run_routine(self, routine):
        """Executes a routine and checks when the routine should next be executed"""
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
