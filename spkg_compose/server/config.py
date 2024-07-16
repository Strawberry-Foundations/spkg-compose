from spkg_compose import init_dir
from spkg_compose.cli.logger import logger
from spkg_compose.utils.colors import *

import yaml
import sys

with open(init_dir + "/data/config.yml", "r") as _config:
    config_data = yaml.load(_config, Loader=yaml.SafeLoader)


class Config:
    def __init__(self):
        try:
            self.data_dir = config_data["server"]["data_dir"]
            self.routines = config_data["routines"]
            self.gh_token = config_data["github"]["tokens"]["primary"]["token"]
        except KeyError as err:
            logger.error(f"Invalid configuration! Please check your configuration file. (Missing key: {err})")
            sys.exit(1)

    def get_token(self, token_id: str):
        self.gh_token = config_data["github"]["tokens"][token_id]["token"]
        logger.info(f"{LIGHT_BLUE}git{RESET}: Using the '{CYAN}{token_id}{RESET}' token as the main token")
        return self.gh_token


config = Config()
