from spkg_compose import SERVER_VERSION, init_dir
from spkg_compose.server.config import config as _cfg
from spkg_compose.core.parser import read
from spkg_compose.cli.logger import logger, current_time
from spkg_compose.server.git import fetch_git
from spkg_compose.utils.colors import *
from spkg_compose.package import SpkgBuild

from datetime import datetime, timedelta

import os
import json
import time
import threading


class Server:
    def __init__(self):
        self.routine_processes = {
            "indexing": self.indexing,
            "fetch_git": self.fetch_git
        }

        self.config = _cfg
        self.index = f"{init_dir}/data/index.json"
        self.running_indexing = False

    def indexing(self):
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
                        logger.info(f"Found new compose package '{CYAN}{name}{CRESET}'")
                        index[name] = {'compose': file_path}

        with open(self.index, 'w') as json_file:
            json.dump(index, json_file, indent=2)
        logger.ok(f"{MAGENTA}routines@indexing{CRESET}: Finished indexing")
        self.running_indexing = False

    def fetch_git(self):
        while True:
            if self.running_indexing:
                time.sleep(1)
                continue
            logger.info(f"{MAGENTA}routines@fetch_git{CRESET}: Starting git fetch")
            fetch_git(self)
            logger.info(f"{MAGENTA}routines@fetch_git{CRESET}: Finished git fetch")
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
        units = {
            'h': 'hours',
            'm': 'minutes',
            's': 'seconds'
        }
        amount = int(interval_str[:-1])
        unit = interval_str[-1]
        kwargs = {units[unit]: amount}
        return timedelta(**kwargs)

    def run(self):
        i = 0
        len_routines = len(self.config.routines)
        try:
            threads = []
            for routine in self.config.routines:
                i += 1
                logger.info(f"Registering routine '{CYAN}{routine['name']}{RESET}' ({i}/{len_routines})")
                thread = threading.Thread(target=self.run_routine, args=(routine,))
                thread.daemon = True
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()
        except KeyboardInterrupt:
            logger.warning("spkg-compose server will be terminated")


def server_main():
    logger.default(f"Starting spkg-compose server v{SERVER_VERSION}")

    server = Server()
    server.run()
