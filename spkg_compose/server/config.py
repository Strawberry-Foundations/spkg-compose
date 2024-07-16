from spkg_compose import init_dir

import yaml

with open(init_dir + "/data/config.yml", "r") as _config:
    config_data = yaml.load(_config, Loader=yaml.SafeLoader)


class Config:
    def __init__(self):
        self.data_dir = config_data["server"]["data_dir"]
        self.routines = config_data["routines"]
        self.gh_token = config_data["github"]["tokens"]["1"]

    def get_token(self, token_id: str):
        self.gh_token = config_data["github"]["tokens"][token_id]
        return self.gh_token


config = Config()
