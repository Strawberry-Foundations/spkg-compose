class SpkgPackageBuilder:
    class Cargo:
        def __init__(self, data: dict):
            self.compose_data = data

            self.build_command = data["Build.cargo"]["Exec"]

    class Any:
        def __init__(self, data: dict):
            self.compose_data = data

            self.build_command = data["Build.any"]["Exec"]
