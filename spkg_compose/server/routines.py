from spkg_compose import SERVER_VERSION, init_dir
from spkg_compose.server.config import config as _cfg
from spkg_compose.server.git import fetch_git
from spkg_compose.core.parser import read
from spkg_compose.cli.logger import logger, current_time
from spkg_compose.server.json import send_json, convert_json_data
from spkg_compose.utils.colors import *
from spkg_compose.utils.time import unix_to_readable, convert_time
from spkg_compose.package import SpkgBuild

from datetime import datetime, timedelta

import os
import sys
import json
import time
import threading
import requests
import socket
import yaml


class Running:
    def __init__(self):
        self.indexing = False
        self.git_checkout = False


rt = Running()


class Routines:
    def __init__(self, server):
        self.server = server

    @staticmethod
    def routine(conflicts: str):
        """-- Routine decorator
            This decorator will wrap some functions that are required for a routine
        """

        def _get_rt(_conflicts):
            match _conflicts:
                case "git_checkout":
                    return rt.git_checkout
                case "indexing":
                    return rt.indexing

        def decorator(func):
            def wrapper(self, *args, **kwargs):
                while True:
                    if _get_rt(conflicts):
                        time.sleep(1)
                        continue

                    rt.indexing = True

                    return func(self, *args, **kwargs)
            return wrapper

        return decorator

    @routine(conflicts="git_checkout")
    def indexing(self):
        """-- Routine for indexing
            This routine checks for new *.spkg files. If there are any new files, this routine will
            append it to the index.json
        """
        i = 0
        while True:
            if self.running.git_checkout:
                time.sleep(1)
                continue
            self.running.indexing = True
            logger.info(f"{MAGENTA}routines@indexing{CRESET}: Starting indexing")
            if os.path.exists(self.index):
                with open(self.index, "r") as json_file:
                    index = json.load(json_file)
            else:
                index = {}

            for root, _, files in os.walk(self.config.data_dir):
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

            with open(self.index, 'w') as json_file:
                json.dump(index, json_file, indent=2)
            if i == 0:
                logger.info(f"{MAGENTA}routines@indexing{CRESET}: Nothing to do, everything up to date.")
            logger.ok(f"{MAGENTA}routines@indexing{CRESET}: Finished indexing, found {i} new packages")
            self.running.indexing = False
            break
