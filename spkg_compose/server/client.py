from spkg_compose.cli.logger import logger
from spkg_compose.package import SpkgBuild
from spkg_compose.server.json import send_json, convert_json_data
from spkg_compose.utils.colors import *

import socket


class BuildServerClient:
    def __init__(self, address: str):
        self.host, self.port = address.split(":")
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self):
        self.socket.connect((self.host, int(self.port)))

    def send(self, data):
        self.socket.send(send_json(data).encode("utf8"))

    def recv(self):
        raw_msg = self.socket.recv(2048).decode('utf-8')
        return convert_json_data(raw_msg)

    def request_slot(self):
        self.send({
            "event": "request_slot"
        })

        message = self.recv()
        response = message["response"]

        if response == "free":
            return True
        else:
            return False

    def disconnect(self):
        self.send({"event": "disconnect"})

    def update_pkg(self, data, package: SpkgBuild):
        self.send({"event": "update_pkg", "data": package.compose_data})

        message = self.recv()
        response = message["response"]

        if response == "accept":
            logger.info(f"{MAGENTA}routines@git.build{CRESET}: Server accepted build request")

        return False
