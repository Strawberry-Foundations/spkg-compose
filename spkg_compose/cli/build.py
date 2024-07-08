from spkg_compose.core.parser import read
from spkg_compose.package import SpkgBuild
from spkg_compose.utils.colors import *

from threading import Thread
from urllib.request import urlopen, urlretrieve
from pathlib import Path

import os
import shutil
import contextlib
import time


def rmfile(file: str, force: bool = False) -> None:
    if force:
        Path(file).unlink(missing_ok=True)
    file_as_path = Path(file)
    with contextlib.suppress(FileNotFoundError):
        file_as_path.unlink()


def mkdir(mk_dir: str, create_parents: bool = False) -> None:
    mk_dir_as_path = Path(mk_dir)
    if not mk_dir_as_path.exists():
        mk_dir_as_path.mkdir(parents=create_parents)


def path_exists(path_str: str) -> bool:
    return Path(path_str).exists()


def get_full_path(path_str: str) -> str:
    return Path(path_str).absolute().as_posix()


def download_file(url: str, path: str) -> None:
    try:
        total_file_size = int(urlopen(url).headers["Content-Length"])
    except TypeError:
        total_file_size = "NaN"

    Thread(target=_print_download_progress, args=(Path(path), total_file_size,), daemon=True).start()

    urlretrieve(url=url, filename=path)

    open(".stop_download_progress", "a").close()
    print("\n", end="")


def _print_download_progress(file_path: Path, total_size) -> None:
    if total_size is None:
        return

    while True:
        if path_exists(".stop_download_progress"):
            rmfile(".stop_download_progress")
            return
        try:
            print("\rDownloading: " + "%.0f" % int(file_path.stat().st_size / 1048576) + "mb / "
                  + "%.0f" % (total_size / 1048576) + "mb", end="", flush=True)
        except FileNotFoundError:
            time.sleep(0.5)


def build(compose_file):
    data = read(compose_file)

    package = SpkgBuild(data)

    print(f"{GREEN}{BOLD}[Compose] Building your package ...{CRESET}")
    print(f"{GREEN}{BOLD}-----------------------------------{CRESET}\n")

    print(f"{GREEN}{BOLD}Name: {CRESET}{package.meta.name}")
    print(f"{GREEN}{BOLD}Description: {CRESET}{package.meta.description}")
    print(f"{GREEN}{BOLD}Version: {CRESET}{package.meta.version}")
    print(f"{GREEN}{BOLD}Architecture: {CRESET}{package.meta.architecture}")
    print(f"{GREEN}{BOLD}Author: {CRESET}{package.meta.author}")
    print(f"{GREEN}{BOLD}Package Format: {CRESET}{package.install.type_as}")

    try:
        os.mkdir("buildpkg")
    except FileExistsError:
        shutil.rmtree("buildpkg")
        os.mkdir("buildpkg")

    if package.prepare.type == "Archive":
        filename = package.prepare.url.split("/")[-1]
        os.chdir("buildpkg")

        download_file(package.prepare.url, filename)

        os.system(f"tar xf {filename}")
        os.chdir(package.build.workdir)
        os.system(package.builder.build_command)

    package.install_pkg.makepkg()

    print()
