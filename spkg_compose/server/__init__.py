from spkg_compose import SERVER_VERSION, init_dir
from spkg_compose.server.config import config as _cfg
from spkg_compose.server.json import send_json, convert_json_data
from spkg_compose.server.routines import Routines
from spkg_compose.utils.colors import *
from spkg_compose.cli.logger import logger


import sys
import threading
import socket


class Server:
    def __init__(self, args):
        self.config = _cfg
        self.args = args
        self.index = f"{init_dir}/data/index.json"

        if "token" in self.args.options:
            try:
                self.config.set_token(self.args.options["token"])
            except KeyError:
                logger.error(f"Token '{CYAN}{self.args.options['token']}{RESET}' not found")
                sys.exit(1)

        self.routines = Routines(self)

    def run(self):
        available_servers = 0

        for name, value in self.config.raw['build_server'].items():
            if not value["enabled"]:
                continue
            host, port = value["address"].split(":")

            logger.info(
                f"{MAGENTA}buildserver@{name}{CRESET}: Trying to connect to build server '{CYAN}{name}{RESET}' "
                f"at {MAGENTA}{host}:{port}{RESET}"
            )

            try:
                _sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                _sock.connect((host, int(port)))
                _sock.send(send_json({
                    "event": "auth",
                    "token": value["token"]
                }).encode("utf8"))

                message = _sock.recv(2048).decode('utf-8')
                message = convert_json_data(message)

                if message["response"]:
                    if message["response"] == "ok":
                        available_servers += 1
                        logger.ok(
                            f"{MAGENTA}buildserver@{name}{CRESET}: Successfully connected to build server "
                            f"'{CYAN}{name}{RESET}' (version {CYAN}{message['version']}{RESET} on "
                            f"{GREEN}{message['architecture']}{RESET})"
                        )
                        _sock.send(send_json({
                            "event": "disconnect",
                        }).encode("utf8"))

                    elif message["response"] == "invalid_token":
                        logger.error(
                            f"{MAGENTA}buildserver@{name}{CRESET}: Invalid token for build server '{CYAN}{name}{RESET}'!"
                        )
                        _sock.close()
                    else:
                        logger.error(
                            f"{MAGENTA}buildserver@{name}{CRESET}: Build server '{CYAN}{name}{RESET}' "
                            f"did not send a valid response! ({message['response']})"
                        )
                        _sock.close()
                else:
                    logger.error(
                        f"{MAGENTA}buildserver@{name}{CRESET}: Build server '{CYAN}{name}{RESET}' "
                        f"did not send a valid response! ({message})"
                    )
                    _sock.close()

            except Exception:
                logger.error(
                    f"{MAGENTA}buildserver@{name}{CRESET}: Build server '{CYAN}{name}{RESET}' is not online! "
                    f"Please check if the build server is running"
                )

        if available_servers == 0:
            logger.error("No build server available! spkg-compose server will be terminated")
            sys.exit(1)

        i = 0
        len_routines = len(self.config.routines)
        try:
            threads = []
            for routine in self.config.routines:
                i += 1
                logger.info(
                    f"Registering routine '{CYAN}{routine['name']}{RESET}' ({i}/{len_routines}), "
                    f"runs every {GREEN}{routine['every']}{RESET}"
                )
                thread = threading.Thread(target=self.routines.run_routine, args=(routine,))
                thread.daemon = True
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()
        except KeyboardInterrupt:
            logger.warning("spkg-compose server will be terminated")


def server_main(args):
    logger.default(f"Starting spkg-compose server v{SERVER_VERSION}")

    server = Server(args)
    server.run()
