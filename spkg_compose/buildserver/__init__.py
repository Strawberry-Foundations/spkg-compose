from spkg_compose import BUILD_SERVER_VERSION, init_dir
from spkg_compose.buildserver.config import config as _cfg
from spkg_compose.cli.logger import logger
from spkg_compose.server import convert_json_data, send_json
from spkg_compose.utils.colors import *

import socket
import threading
import sys
import time


class BuildServer:
    def __init__(self, args):
        self.config = _cfg
        self.args = args
        self.index = f"{init_dir}/data/index.json"

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.running = False
        self.addresses = {}

    def connection_thread(self):
        while self.running:
            try:
                client, address = self.socket.accept()
            except Exception as err:
                logger.error(f"An error occurred while a client was trying to connect {err}")
                break

            self.addresses[client] = address

            logger.info(f"Client '{address[0]}' connected")
            threading.Thread(target=self.client_thread, args=(client,)).start()

    def client_thread(self, client: socket.socket):
        while self.running:
            try:
                message = client.recv(2048).decode('utf-8')
                message = convert_json_data(message)
                event = message["event"]

                match event:
                    case "test_connection":
                        token = message["token"]

                        if token != self.config.token:
                            client.send(send_json({
                                "response": "invalid_token",
                            }).encode("utf8"))
                        else:
                            client.send(send_json({
                                "response": "ok",
                            }).encode("utf8"))
            except:
                logger.error(f"Failed to communicate with client")
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
