from sys import argv


class Args:
    def __init__(self):
        self.args = argv

    def get(self, index: int):
        return self.args[index]
