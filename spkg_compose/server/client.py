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

    def auth(self, token: str, server_name: str, silent: bool = False):
        self.send({
            "event": "auth",
            "token": token
        })

        message = self.recv()
        response = message["response"]

        if response == "ok":
            if not silent:
                logger.ok(
                    f"{MAGENTA}routines@git.build.{server_name}{CRESET}: Authentication successful with server "
                    f"'{CYAN}{server_name}{RESET}'"
                )

        elif message["response"] == "invalid_token":
            logger.error(
                f"{MAGENTA}routines@git.build{CRESET}: Invalid token for build server '{CYAN}{server_name}{RESET}'!"
            )
        else:
            logger.error(f"{MAGENTA}routines@git.build{CRESET}: Invalid response from build server!")

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

    def update_pkg(self, data, package: SpkgBuild, server_name: str):
        self.send({"event": "update_pkg", "data": package.compose_data})

        message = self.recv()
        response = message["response"]

        if response == "accept":
            logger.info(f"{MAGENTA}routines@git.build.{server_name}{CRESET}: Server accepted build request")
        else:
            logger.warning(f"{MAGENTA}routines@git.build.{server_name}{CRESET}: Server did not accepted build request")
            return False

        logger.info(
            f"{MAGENTA}routines@git.build.{server_name}{CRESET}: Starting build process ..."
        )
        message = self.recv()
        response = message["response"]

        if response == "success":
            _package = message["package_file"]
            logger.info(
                f"{MAGENTA}routines@git.build.{server_name}{CRESET}: Package successfully build as "
                f"'{CYAN}{_package}{RESET}'"
            )
            return True
        else:
            return False
