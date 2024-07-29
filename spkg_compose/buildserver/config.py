import os.path

from spkg_compose import init_dir
from spkg_compose.cli.logger import logger
from spkg_compose.utils.colors import *

import yaml
import sys
import random
import string


def generate_token(length=32):
    characters = string.ascii_letters + string.digits

    token = ''.join(random.choice(characters) for i in range(length))
    return token


DEFAULT_CONFIG = """server:
  name: Local Computer
  tags: [x86_64, linux]
  address: 127.0.0.1
  port: 3086
  token: sf_spc_some_random_token
  repo_url: http://localhost:3087
"""

try:
    with open(init_dir + "/data/buildserver.yml", "r") as _config:
        config_data = yaml.load(_config, Loader=yaml.SafeLoader)
except FileNotFoundError:
    logger.warning("Configuration file does not exist. Creating a new one...")
    if not os.path.exists(init_dir + "/data"):
        os.mkdir(init_dir + "/data")

    with open(init_dir + "/data/buildserver.yml", "w") as _config:
        _config.write(DEFAULT_CONFIG.replace("sf_spc_some_random_token", f"sf_spc_{generate_token()}"))
    logger.ok(f"Config file created ({GREEN}{init_dir}/data/buildserver.yml{RESET}).")
    logger.info("Please adjust the configuration according to your wishes and then restart the server.")
    sys.exit(0)


class Config:
    def __init__(self):
        try:
            self.name = config_data["server"]["name"]
            self.tags = config_data["server"]["tags"]
            self.address = config_data["server"]["address"]
            self.port = config_data["server"]["port"]
            self.token = config_data["server"]["token"]
            self.repo_url = config_data["server"]["repo_url"]

        except KeyError as err:
            logger.error(f"Invalid configuration! Please check your configuration file. (Missing key: {err})")
            sys.exit(1)


config = Config()
