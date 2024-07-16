from spkg_compose import BUILD_SERVER_VERSION, init_dir
from spkg_compose.buildserver import config as _cfg
from spkg_compose.cli.logger import logger


class BuildServer:
    def __init__(self, args):
        self.config = _cfg
        self.args = args
        self.index = f"{init_dir}/data/index.json"

    def run(self):
        pass


def build_server_main(args):
    logger.default(f"Starting spkg-compose build server v{BUILD_SERVER_VERSION}")

    server = BuildServer(args)
    server.run()
