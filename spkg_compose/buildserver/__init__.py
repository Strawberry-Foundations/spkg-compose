from spkg_compose import BUILD_SERVER_VERSION, init_dir
from spkg_compose.buildserver.config import config as _cfg
from spkg_compose.cli.build import download_file
from spkg_compose.cli.logger import logger
from spkg_compose.package import SpkgBuild
from spkg_compose.server import convert_json_data, send_json
from spkg_compose.utils.colors import *

import socket
import threading
import sys
import os
import shutil

addresses = {}
authenticated = {}


class Client:
    def __init__(self, client: socket.socket, address):
        self.socket = client
        self.address = address[0]

    def recv(self):
        raw_msg = self.socket.recv(2048).decode('utf-8')
        return convert_json_data(raw_msg)

    def send(self, data):
        self.socket.send(send_json(data).encode("utf8"))

    def close(self):
        self.socket.close()
        del addresses[self.socket]
        logger.info(f"Client '{CYAN}{self.address}{RESET}' disconnected")
        exit()

    def is_authenticated(self):
        if authenticated.__contains__(self):
            if authenticated[self]:
                return True
            logger.info(
                f"{LIGHT_BLUE}auth{RESET}: Unauthenticated client '{CYAN}{self.address}{CRESET} connected & "
                f"tried to run job'"
            )
            return False
        logger.info(
            f"{LIGHT_BLUE}auth{RESET}: Unauthenticated client '{CYAN}{self.address}{CRESET} connected & "
            f"tried to run job'"
        )
        return False

    def not_authenticated(self):
        self.send({"response": "not_authenticated"})
        self.close()


class BuildServer:
    def __init__(self, args):
        self.config = _cfg
        self.args = args
        self.index = f"{init_dir}/data/index.json"

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.running = False
        self.is_build_process = False

    def connection_thread(self):
        while self.running:
            try:
                client, address = self.socket.accept()
            except Exception as err:
                logger.error(f"An error occurred while a client was trying to connect {err}")
                break

            addresses[client] = address

            logger.info(f"Client '{CYAN}{address[0]}{RESET}' connected")
            client = Client(client, address)
            threading.Thread(target=self.client_thread, args=(client,)).start()

    def client_thread(self, client: Client):
        while self.running:
            try:
                message = client.recv()
                event = message["event"]

                match event:
                    case "test_connection":
                        token = message["token"]
                        logger.info(
                            f"{LIGHT_BLUE}auth{RESET}: Client '{CYAN}{client.address}{CRESET}' sent "
                            f"{GREEN}event@test_connection{RESET}"
                        )

                        if token != self.config.token:
                            client.send({"response": "invalid_token"})
                        else:
                            client.send({"response": "ok", "version": BUILD_SERVER_VERSION})

                    case "auth":
                        token = message["token"]
                        logger.info(
                            f"{LIGHT_BLUE}auth{RESET}: Client '{CYAN}{client.address}{CRESET}' authenticated with token"
                        )

                        if token != self.config.token:
                            client.send({"response": "invalid_token"})
                            logger.warning(f"{LIGHT_BLUE}auth{RESET}: Invalid token from '{CYAN}{client.address}{CRESET}'")
                        else:
                            client.send({"response": "ok"})
                            logger.ok(f"{LIGHT_BLUE}auth{RESET}: Token is valid")
                            authenticated[client] = True

                    case "disconnect":
                        client.close()

                    case "request_slot":
                        if not client.is_authenticated():
                            return client.not_authenticated()

                        logger.info(f"Slot request from '{CYAN}{client.address}{CRESET}'")
                        if self.is_build_process:
                            status = "full"
                            logger.warning("No available slot")
                        else:
                            status = "free"

                        client.send({"response": status})

                    case "update_pkg":
                        if not client.is_authenticated():
                            return client.not_authenticated()

                        package = SpkgBuild(message["data"])
                        logger.routine(
                            f"{MAGENTA}rt@build{CRESET}: Build request from '{CYAN}{client.address}{CRESET}' for "
                            f"package '{GREEN}{package.meta.id}{RESET}', version {CYAN}{package.meta.version}{RESET}"
                        )

                        client.send({"response": "accept"})
                        logger.routine(f"{MAGENTA}rt@build{CRESET}: Build request accepted")

                        logger.routine(
                            f"{MAGENTA}rt@build{CRESET}: Preparing build process for "
                            f"{package.meta.id}-{package.meta.version}"
                        )

                        try:
                            os.mkdir("_work")
                        except FileExistsError:
                            shutil.rmtree("_work")
                            os.mkdir("_work")
        
                        if package.prepare.type == "Archive":
                            filename = package.prepare.url.split("/")[-1]
                            os.chdir("_work")
        
                            download_file(package.prepare.url, filename)
        
                            os.system(f"tar xf {filename}")
                            os.chdir(package.build.workdir)

                            logger.routine(
                                f"{MAGENTA}rt@build{CRESET}: Building package {package.meta.id}-{package.meta.version}"
                            )
                            os.system(package.builder.build_command)

                        logger.routine(
                            f"{MAGENTA}rt@build{CRESET}: Creating binpkg ..."
                        )
                        package = package.install_pkg.makepkg()
        
                        logger.ok(f"{MAGENTA}rt@build{CRESET}: Package successfully build as '{CYAN}{package}{RESET}'")
                        client.send({"response": "success", "package_file": package})

            except KeyError as err:
                logger.warning(f"Client '{CYAN}{client.address}{RESET}' disconnected unexpected ({err})")
                break

    def run(self):
        try:
            try:
                self.socket.bind((self.config.address, self.config.port))
                self.socket.listen()
                logger.ok(f"Listening on {MAGENTA}{self.config.address}:{self.config.port}{RESET}")
                self.running = True

            except OSError:
                logger.error(f"Address already in use ({MAGENTA}{self.config.address}:{self.config.port}{RESET})")
                sys.exit(1)

            connection = threading.Thread(target=self.connection_thread())
            connection.start()
            connection.join()
        except KeyboardInterrupt:
            logger.warning("spkg-compose build server will be terminated")


def build_server_main(args):
    logger.default(f"Starting spkg-compose build server v{BUILD_SERVER_VERSION}")

    server = BuildServer(args)
    server.run()
