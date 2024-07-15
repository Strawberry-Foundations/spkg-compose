from spkg_compose import SERVER_VERSION, init_dir
from spkg_compose.server.config import config
from spkg_compose.core.parser import read
from spkg_compose.cli.logger import logger

import os
import json

from spkg_compose.package import SpkgBuild


class Server:
    def __init__(self):
        pass

    def index_spkg_files(self, directory: str, output_file: str):
        logger.info("Starting indexing")
        if os.path.exists(output_file):
            with open(output_file, 'r') as json_file:
                index = json.load(json_file)
        else:
            index = {}

        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.spkg'):
                    file_path = os.path.join(root, file)

                    data = read(file_path)
                    package = SpkgBuild(data)
                    name = package.meta.id

                    if name not in index:
                        index[name] = {'compose': file_path}

        with open(output_file, 'w') as json_file:
            json.dump(index, json_file, indent=2)
        logger.info("Finished indexing")

    def run(self):
        self.index_spkg_files(config.data_dir, f"{init_dir}/data/index.json")


def server_main():
    logger.info(f"Starting spkg-compose server v{SERVER_VERSION}")

    server = Server()
    server.run()
