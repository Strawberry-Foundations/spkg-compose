from spkg_compose.core.parser import read
from spkg_compose.core.git import get_git_url
from spkg_compose.package import SpkgBuild
from spkg_compose.utils.colors import *

from threading import Thread
from urllib.request import urlopen, urlretrieve
from pathlib import Path

import os
import shutil
import contextlib
import time
import platform


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
        total_file_size = "N/A"

    Thread(target=_print_download_progress, args=(Path(path), total_file_size), daemon=True).start()

    urlretrieve(url=url, filename=path)

    open(".stop_download_progress", "a").close()
    print(f"{BACK_GREEN}   OK   {BACK_RESET}  Finished download")


def download_file_simple(url: str, path: str) -> None:
    urlretrieve(url=url, filename=path)


def _print_download_progress(file_path: Path, total_size) -> None:
    if total_size is None:
        return

    if total_size != "N/A":
        total_size = "%.0f" % (total_size / 1048576)

    while True:
        if path_exists(".stop_download_progress"):
            rmfile(".stop_download_progress")
            return
        try:
            print("\rDownloading: " + "%.0f" % int(file_path.stat().st_size / 1048576) + "MB / "
                  + total_size + "MB", end="", flush=True)
        except FileNotFoundError:
            time.sleep(0.5)


def build(compose_file):
    def _get_arch(arch: str):
        if arch == "%runtime_arch%":
            return f"({platform.machine()})"

    data = read(compose_file)

    package = SpkgBuild(data)

    print(f"{BACK_CYAN}  INFO  {BACK_RESET}  Starting package build process")

    print(f"  {CYAN}{BOLD}Package details:{CRESET}")
    print(f"    {GREEN}{BOLD}Name: {CRESET}{package.meta.name}")
    print(f"    {GREEN}{BOLD}ID: {CRESET}{package.meta.id}")
    print(f"    {GREEN}{BOLD}Description: {CRESET}{package.meta.description}")
    print(f"    {GREEN}{BOLD}Version: {CRESET}{package.meta.version}")
    print(f"    {GREEN}{BOLD}Architecture: {CRESET}{package.meta.architecture} {_get_arch(package.meta.architecture)}")
    print(f"    {GREEN}{BOLD}Author: {CRESET}{package.meta.author}")
    print(f"    {GREEN}{BOLD}Source: {CRESET}{package.meta.source}")
    print(f"    {GREEN}{BOLD}Package Format: {CRESET}{package.install.type_as}\n")

    try:
        os.mkdir("_work")
    except FileExistsError:
        shutil.rmtree("_work")
        os.mkdir("_work")

    print(f"{BACK_CYAN}  INFO  {BACK_RESET}  Preparing for type {CYAN}{package.prepare.type}{RESET}")

    match package.prepare.type.lower():
        case "git":
            os.chdir("_work")
            url = get_git_url(package)

            print(f"{BACK_CYAN}  INFO  {BACK_RESET}  Cloning git repository {CYAN}{url}{RESET}")

            if package.prepare.branch is not None:
                os.system(f"git clone {url} -b {package.prepare.branch}")
            else:
                os.system(f"git clone {url}")

            os.chdir(package.build.workdir)

            print(f"{BACK_CYAN}  INFO  {BACK_RESET}  Running build command '{CYAN}{package.builder.build_command}{RESET}'")
            os.system(package.builder.build_command)

        case "archive":
            filename = package.prepare.url.split("/")[-1]
            os.chdir("_work")
            download_file(package.prepare.url, filename)

            print(f"{BACK_CYAN}  INFO  {BACK_RESET}  Extracting archive {CYAN}{filename}{RESET}")
            os.system(f"tar xf {filename}")
            os.chdir(package.build.workdir)

            print(f"{BACK_CYAN}  INFO  {BACK_RESET}  Running build command '{CYAN}{package.builder.build_command}{RESET}'")
            os.system(package.builder.build_command)

        case "binaryarchive":
            filename = package.prepare.url.split("/")[-1]
            os.chdir("_work")
            download_file(package.prepare.url, filename)

            print(f"{BACK_CYAN}  INFO  {BACK_RESET}  Extracting archive {CYAN}{filename}{RESET}")
            os.system(f"tar xf {filename}")
            os.chdir(package.build.workdir)

    package = package.install_pkg.makepkg()

    print(f"\n{BACK_GREEN}   OK   {BACK_RESET}  Package successfully build as '{package}'")
