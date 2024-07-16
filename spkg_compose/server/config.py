from spkg_compose import init_dir
from spkg_compose.cli.logger import logger
from spkg_compose.utils.colors import *

import yaml
import sys

DEFAULT_CONFIG = """server:
  data_dir: /path/to/your/repo

build_server:
  main:
    name: My build server
    tags: [x86_64, linux]
    address: 127.0.0.1:3086
    token: insert_token_here
    
routines:
  - name: index
    process: indexing
    every: 30m
  - name: fetch-git
    process: git
    every: 15m

github:
  tokens:
    primary:
      token: your_gh_token
"""

try:
    with open(init_dir + "/data/config.yml", "r") as _config:
        config_data = yaml.load(_config, Loader=yaml.SafeLoader)
except FileNotFoundError:
    logger.warning("Configuration file does not exist. Creating a new one...")
    with open(init_dir + "/data/config.yml", "w") as _config:
        _config.write(DEFAULT_CONFIG)
    logger.ok(f"Config file created ({GREEN}{init_dir}/data/config.yml{RESET}).")
    logger.info("Please adjust the configuration according to your wishes and then restart the server.")
    sys.exit(0)


class Config:
    def __init__(self):
        try:
            self.data_dir = config_data["server"]["data_dir"]
            self.routines = config_data["routines"]
            self.gh_token = config_data["github"]["tokens"]["primary"]["token"]
            self.build_server = config_data["build_server"]
        except KeyError as err:
            logger.error(f"Invalid configuration! Please check your configuration file. (Missing key: {err})")
            sys.exit(1)

    def set_token(self, token_id: str):
        self.gh_token = config_data["github"]["tokens"][token_id]["token"]
        logger.info(f"{LIGHT_BLUE}git{RESET}: Using the '{CYAN}{token_id}{RESET}' token as the main token")
        return self.gh_token


config = Config()
