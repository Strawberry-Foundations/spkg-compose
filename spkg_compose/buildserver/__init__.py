import sys

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


class BuildServer:
    def __init__(self, args):
        self.config = _cfg
        self.args = args
        self.index = f"{init_dir}/data/index.json"

    def run(self):

        pass


def build_server_main(args):
    logger.default(f"Starting spkg-compose build server v{SERVER_VERSION}")

    server = BuildServer(args)
    server.run()
