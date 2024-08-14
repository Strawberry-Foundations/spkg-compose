from spkg_compose import BUILD_SERVER_VERSION, init_dir
from spkg_compose.core.git import get_git_url
from spkg_compose.buildserver.config import config as _cfg
from spkg_compose.cli.build import download_file_simple
from spkg_compose.cli.logger import logger
from spkg_compose.package import SpkgBuild
from spkg_compose.server import convert_json_data, send_json
from spkg_compose.utils.colors import *

import socket
import threading
import sys
import os
import shutil
import json.decoder
import platform
import requests

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
                try:
                    message = client.recv()
                except json.decoder.JSONDecodeError:
                    logger.info(f"Client '{CYAN}{client.address}{RESET}' disconnected")
                    break

                event = message["event"]

                match event:
                    case "auth":
                        token = message["token"]
                        logger.info(
                            f"{LIGHT_BLUE}auth{RESET}: Client '{CYAN}{client.address}{CRESET}' authenticated with token"
                        )

                        if token != self.config.token:
                            client.send({"response": "invalid_token"})
                            logger.warning(
                                f"{LIGHT_BLUE}auth{RESET}: Invalid token from '{CYAN}{client.address}{CRESET}'")
                            client.close()
                        else:
                            client.send({
                                "response": "ok",
                                "version": BUILD_SERVER_VERSION,
                                "architecture": platform.machine()
                            })
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
                        repo_url = message["repo_url"]

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

                        logger.routine(f"{MAGENTA}rt@build{CRESET}: Preparing for type {CYAN}{package.prepare.type}{RESET}")
                        match package.prepare.type.lower():
                            case "git":
                                os.chdir("_work")
                                url = get_git_url(package)

                                logger.routine(f"{MAGENTA}rt@build{CRESET}: Cloning git repository {CYAN}{url}{RESET}")

                                if package.prepare.branch is not None:
                                    os.system(f"git clone {url} -b {package.prepare.branch}")
                                else:
                                    os.system(f"git clone {url}")

                                os.chdir(package.build.workdir)

                                logger.routine(f"{MAGENTA}rt@build{CRESET}: Building package {package.meta.id}-{package.meta.version}")
                                os.system(package.builder.build_command)

                            case "archive":
                                filename = package.prepare.url.split("/")[-1]
                                os.chdir("_work")

                                try:
                                    download_file_simple(package.prepare.url, filename)
                                except Exception as err:
                                    logger.warning(f"Exception occurred {err}")

                                os.system(f"tar xf {filename}")
                                os.chdir(package.build.workdir)

                                logger.routine(f"{MAGENTA}rt@build{CRESET}: Building package {package.meta.id}-{package.meta.version}")
                                os.system(package.builder.build_command)

                            case "binaryarchive":
                                filename = package.prepare.url.split("/")[-1]
                                os.chdir("_work")

                                try:
                                    download_file_simple(package.prepare.url, filename)
                                except Exception as err:
                                    logger.warning(f"Exception occurred {err}")

                                os.system(f"tar xf {filename}")
                                os.chdir(package.build.workdir)

                        logger.routine(
                            f"{MAGENTA}rt@build{CRESET}: Creating binpkg ..."
                        )
                        build_package = package.install_pkg.makepkg()

                        logger.ok(f"{MAGENTA}rt@build{CRESET}: Package successfully build as '{CYAN}{build_package}{RESET}'")
                        logger.info(f"{MAGENTA}rt@build{CRESET}: Uploading package to {BLUE}{repo_url}{RESET} ...")
                        url = f"{repo_url}/upload"

                        headers = {
                            "Authorization": f"Bearer {self.config.token}",
                            "Package": package.meta.id
                        }
                        files = {
                            "file": open(f"{init_dir}/{build_package}", "rb")
                        }
                        try:
                            response = requests.post(url, headers=headers, files=files)
                        except Exception as err:
                            logger.warning(f"{MAGENTA}rt@build{CRESET}: Apparently the HTTP API is not available{RESET}")
                            logger.warning(f"{MAGENTA}rt@build{CRESET}: Error details: {err}{RESET}")
                            logger.info(
                                f"{MAGENTA}rt@build{CRESET}: Removing locally saved package "
                                f"'{CYAN}{build_package}{RESET}'"
                            )
                            os.remove(f"{init_dir}/{build_package}")
                            logger.warning(f"{MAGENTA}rt@build{CRESET}: Build not succeeded{RESET}")
                            return client.send({"response": "failed"})

                        match response.status_code:
                            case 403:
                                logger.info(
                                    f"{MAGENTA}rt@build{CRESET}: This build server does not have access to the HTTP "
                                    f"API. Check the token in your config{RESET}"
                                )
                                logger.info(
                                    f"{MAGENTA}rt@build{CRESET}: Removing locally saved package "
                                    f"'{CYAN}{build_package}{RESET}'"
                                )
                                os.remove(f"{init_dir}/{build_package}")
                                logger.warning(f"{MAGENTA}rt@build{CRESET}: Build not succeeded{RESET}")
                                return client.send({"response": "failed"})
                            case 200:
                                logger.info(f"{MAGENTA}rt@build{CRESET}: {response.text}{RESET}")
                            case _:
                                logger.info(
                                    f"{MAGENTA}rt@build{CRESET}: Got unknown status code from HTTP API: "
                                    f"{response.status_code}{RESET}"
                                )

                        logger.info(f"{MAGENTA}rt@build{CRESET}: Removing locally saved package '{CYAN}{build_package}{RESET}'")
                        os.remove(f"{init_dir}/{build_package}")

                        logger.ok(f"{MAGENTA}rt@build{CRESET}: Build succeeded{RESET}")
                        client.send({"response": "success", "package_file": build_package})

            except Exception as err:
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
    logger.default(f"Starting spkg-compose build server v{BUILD_SERVER_VERSION} for {CYAN}{platform.machine()}{RESET}")
    logger.info(f"{MAGENTA}server@meta{RESET}: Server Name: {CYAN}{_cfg.name}{RESET}")
    logger.info(f"{MAGENTA}server@meta{RESET}: Server Tags: {CYAN}{f'{GRAY}, {CYAN}'.join(_cfg.tags)}{RESET}")

    server = BuildServer(args)
    server.run()
