from spkg_compose.cli.logger import logger, RtLogger
from spkg_compose.package import SpkgBuild
from spkg_compose.server.json import send_json, convert_json_data
from spkg_compose.utils.colors import *

import socket


class BuildServerClient:
    def __init__(self, address: str, rt_logger: RtLogger):
        self.host, self.port = address.split(":")
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.logger = rt_logger

    def connect(self):
        try:
            self.socket.connect((self.host, int(self.port)))
            return True
        except:
            logger.warning(
                f"{MAGENTA}buildserver@{self.host}{CRESET}: Connection failed while trying to connect to "
                f"{MAGENTA}{self.host}:{self.port}{RESET}"
            )
            return False

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
                self.logger.ok(
                    message=f"Authentication successful with server '{CYAN}{server_name}{RESET}'",
                    suffix=f"build.{server_name}"
                )

        elif message["response"] == "invalid_token":
            self.logger.error(f"Invalid token for build server '{CYAN}{server_name}{RESET}'!", suffix="build")
        else:
            self.logger.error(f"Invalid response from build server!", suffix="build")

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
            self.logger.info(f"Server accepted build request", suffix=f"build.{server_name}")
        else:
            self.logger.warning(f"Server did not accepted build request", suffix=f"build.{server_name}")
            return False

        self.logger.info(
            f"Starting build process ...", suffix=f"build.{server_name}"
        )
        message = self.recv()
        response = message["response"]

        if response == "success":
            _package = message["package_file"]
            self.logger.info(
                f"Package successfully build as '{CYAN}{_package}{RESET}'", suffix=f"build.{server_name}"
            )
            return True
        else:
            return False
