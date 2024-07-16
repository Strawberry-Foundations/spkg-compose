from sys import argv


class Args:
    def __init__(self):
        self.args = argv
        self.options = self.parse_args()

    def get(self, index: int):
        return self.args[index]

    def parse_args(self):
        arguments = {}
        i = 0
        while i < len(self.args):
            if self.args[i].startswith('--'):
                key = self.args[i].lstrip('-')
                if i + 1 < len(self.args) and not self.args[i + 1].startswith('--'):
                    arguments[key] = self.args[i + 1]
                    i += 1
                else:
                    arguments[key] = None
            i += 1
        return arguments

    def index_start(self, pos: int):
        self.args = self.args[:pos]
        return self
