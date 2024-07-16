import shutil

from spkg_compose import execution_dir
from binpkg import BinPkg
from binpkg.metadata import Metadata

import platform
import os


class SpkgBinPkgFormat:
    def __init__(self, raw_data: dict):
        self.compose_data = raw_data

        self.prefix = raw_data["Install.binpkg"]["Prefix"]
        self.target = raw_data["Install.binpkg"]["Target"]
        self.build_workdir = raw_data["Build"]["Workdir"]

        self.name = self.compose_data["Meta"]["Name"]
        self.id = self.compose_data["Meta"]["Id"]
        self.description = self.compose_data["Meta"]["Description"]
        self.version = self.compose_data["Meta"]["Version"]
        self.architecture = self.compose_data["Meta"]["Architecture"]
        self.author = self.compose_data["Meta"]["Author"]

    def makepkg(self):
        os.chdir(f"{execution_dir}/_work")
        try:
            os.mkdir("_binpkg")
        except FileExistsError:
            shutil.rmtree("_binpkg")
            os.mkdir("_binpkg")
        os.chdir("_binpkg")

        path = ""

        if not self.prefix == "/":
            if self.prefix.startswith("/"):
                path = self.prefix[1:]

            directories = path.split("/")

            current_path = ""
            for directory in directories:
                current_path = os.path.join(current_path, directory)
                if not os.path.exists(current_path):
                    os.makedirs(current_path)

        os.chdir(f"{execution_dir}/_work")
        os.system(f"cp -r {self.build_workdir}/{self.target} _binpkg/{self.prefix}")

        if self.architecture == "%runtime_arch%":
            self.architecture = platform.machine()

        if os.path.exists(f"{self.id}-{self.version}-{self.architecture}.binpkg"):
            os.remove(f"{self.id}-{self.version}-{self.architecture}.binpkg")

        if os.path.exists(f"../{self.id}-{self.version}-{self.architecture}.binpkg"):
            os.remove(f"../{self.id}-{self.version}-{self.architecture}.binpkg")

        BinPkg.create(
            meta=Metadata(
                name=self.name,
                id=self.id,
                version=self.version,
                description=self.description,
                architecture=self.architecture,
                author=self.author
            ),
            source_dir="./_binpkg",
            output_file=f"{self.id}-{self.version}-{self.architecture}.binpkg"
        )

        os.system(f"mv {self.id}-{self.version}-{self.architecture}.binpkg ..")

        return f"{self.id}-{self.version}-{self.architecture}.binpkg"
