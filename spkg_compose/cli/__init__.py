from spkg_compose.cli.build import build

from sys import argv


class Args:
    def __init__(self, cmd_args):
        self.args = cmd_args


args = Args(cmd_args=argv)

match args:
    case _:
        if len(args.args) < 2:
            print("Missing compose file")
            exit(1)
        build(compose_file=args.args[1])
