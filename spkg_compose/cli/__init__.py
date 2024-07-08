from spkg_compose.cli.build import build
from spkg_compose.utils.colors import *

from sys import argv


class Args:
    def __init__(self, cmd_args):
        self.args = cmd_args


args = Args(cmd_args=argv)

match args:
    case _:
        if len(args.args) < 2:
            print(f"{BACK_RED}  ERROR  {BACK_RESET}  Missing compose file!")
            exit(1)
        build(compose_file=args.args[1])
