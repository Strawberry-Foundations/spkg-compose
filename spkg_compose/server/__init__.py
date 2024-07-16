from spkg_compose import SERVER_VERSION, init_dir
from spkg_compose.server.config import config as _cfg
from spkg_compose.server.git import fetch_git
from spkg_compose.core.parser import read
from spkg_compose.cli.logger import logger, current_time
from spkg_compose.utils.colors import *
from spkg_compose.utils.time import unix_to_readable
from spkg_compose.package import SpkgBuild

from datetime import datetime, timedelta

import os
import json
import time
import threading
import requests


def calculate_percentage(total, value):
    """Calculate the percentage of value from total and return colored output."""
    if total == 0:
        return "Total can't be zero"

    percentage = (value / total) * 100

    if percentage > 60:
        color = GREEN
    elif percentage > 30:
        color = YELLOW
    else:
        color = RED

    reset_color = "\033[0m"
    return f"{color}{value} ({percentage:.2f}%) {reset_color}"


class Server:
    def __init__(self, args):
        self.routine_processes = {
            "indexing": self.indexing,
            "git": self.fetch_git
        }
        self.units = {
            'h': 'hours',
            'm': 'minutes',
            's': 'seconds'
        }

        self.config = _cfg
        self.args = args
        self.index = f"{init_dir}/data/index.json"
        self.running_indexing = False
        self.running_gitfetch = False

        self.config.get_token("secondary")

    def indexing(self):
        i = 0
        while True:
            if self.running_gitfetch:
                time.sleep(1)
                continue
            self.running_indexing = True
            logger.info(f"{MAGENTA}routines@indexing{CRESET}: Starting indexing")
            if os.path.exists(self.index):
                with open(self.index, 'r') as json_file:
                    index = json.load(json_file)
            else:
                index = {}

            for root, _, files in os.walk(self.config.data_dir):
                for file in files:
                    if file.endswith('.spkg'):
                        file_path = os.path.join(root, file)

                        data = read(file_path)
                        package = SpkgBuild(data)
                        name = package.meta.id

                        if name not in index:
                            i += 1
                            logger.info(f"{MAGENTA}routines@indexing{CRESET}: Found new compose package '{CYAN}{name}{CRESET}'")
                            index[name] = {
                                'compose': file_path,
                                'last_commit': '',
                                'specfile': file_path.replace("/compose.spkg", "/specfile.yml")
                            }

            with open(self.index, 'w') as json_file:
                json.dump(index, json_file, indent=2)
            if i == 0:
                logger.info(f"{MAGENTA}routines@indexing{CRESET}: Nothing to do, everything up to date.")
            logger.ok(f"{MAGENTA}routines@indexing{CRESET}: Finished indexing, found {i} new packages")
            self.running_indexing = False
            break

    def fetch_git(self):
        while True:
            if self.running_indexing:
                time.sleep(1)
                continue
            self.running_gitfetch = True
            logger.info(f"{MAGENTA}routines@git{CRESET}: Starting git fetch")
            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'Authorization': f'Bearer {self.config.gh_token}'
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
                break

            fetch_git(self)
            logger.info(f"{MAGENTA}routines@git{CRESET}: Finished git fetch")
            self.running_gitfetch = False
            break

    def run_routine(self, routine):
        process_name = routine['process']
        every = routine['every']
        interval = self.parse_interval(every)

        next_run = datetime.now()

        while True:
            time_fmt = current_time("%Y-%m-%d %H:%M:%S")
            now = datetime.now()

            if now >= next_run:
                logger.routine(f"Running routine '{CYAN}{routine['name']}{RESET}' at {time_fmt}")
                self.routine_processes[process_name]()
                next_run = now + interval

            time.sleep(1)

    def parse_interval(self, interval_str):
        amount = int(interval_str[:-1])
        unit = interval_str[-1]
        kwargs = {self.units[unit]: amount}
        return timedelta(**kwargs)

    def run(self):
        i = 0
        len_routines = len(self.config.routines)
        try:
            threads = []
            for routine in self.config.routines:
                i += 1
                logger.info(
                    f"Registering routine '{CYAN}{routine['name']}{RESET}' ({i}/{len_routines}), "
                    f"runs every {GREEN}{routine['every']}{RESET}"
                )
                thread = threading.Thread(target=self.run_routine, args=(routine,))
                thread.daemon = True
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()
        except KeyboardInterrupt:
            logger.warning("spkg-compose server will be terminated")


def server_main(args):
    logger.default(f"Starting spkg-compose server v{SERVER_VERSION}")

    server = Server(args)
    server.run()
