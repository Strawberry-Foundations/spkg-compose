from spkg_compose.cli.build import build
from spkg_compose.cli.args import Args
from spkg_compose.cli.help import help_cmd
from spkg_compose.utils.colors import *

args = Args()

try:
    command = args.get(1)
except IndexError:
    help_cmd()
    exit(0)


match args.args[1]:
    case "help":
        help_cmd()
    case "build":
        if len(args.args) < 3:
            print(f"{BACK_RED}  ERROR  {BACK_RESET}  Missing compose file!")
            exit(1)
        try:
            build(compose_file=args.args[2])
        except KeyboardInterrupt:
            print(f"{BACK_YELLOW} WARNING {BACK_RESET}  Canceling operation")
