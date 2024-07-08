import platform

from spkg_compose import execution_dir

import os


class SpkgDebPkgFormat:
    def __init__(self, raw_data: dict):
        self.compose_data = raw_data

        self.prefix = raw_data["Install.deb"]["Prefix"]
        self.target = raw_data["Install.deb"]["Target"]
        self.build_workdir = raw_data["Build"]["Workdir"]

        self.name = self.compose_data["Meta"]["Name"]
        self.id = self.compose_data["Meta"]["Id"]
        self.description = self.compose_data["Meta"]["Description"]
        self.version = self.compose_data["Meta"]["Version"]
        self.architecture = self.compose_data["Meta"]["Architecture"]
        self.author = self.compose_data["Meta"]["Author"]

    def makepkg(self):
        os.chdir(f"{execution_dir}/_work")
        os.mkdir("_deb")
        os.chdir("_deb")

        os.mkdir("DEBIAN")

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
        os.system(f"cp -r {self.build_workdir}/{self.target} _deb/{self.prefix}")

        architecture = "all"

        if self.architecture == "OnBuildSystem":
            match platform.machine():
                case "x86_64":
                    architecture = "amd64"
                case "aarch64":
                    architecture = "arm64"
                case "x86":
                    architecture = "i386"

        with open("_deb/DEBIAN/control", "w") as _deb_control:
            _deb_control.write(f"""Package: {self.id}
Version: {self.version}
Architecture: {architecture}
Maintainer: {self.author}
Description: {self.description}
""")

            _deb_control.close()

            os.chdir(f"{execution_dir}/_work")

            os.system("dpkg-deb --build _deb")
            os.system(f"mv _deb.deb {self.id}-{self.version}-{architecture}.deb")
            os.system(f"mv {self.id}-{self.version}-{architecture}.deb ..")

            return f"{self.id}-{self.version}-{architecture}.deb"
