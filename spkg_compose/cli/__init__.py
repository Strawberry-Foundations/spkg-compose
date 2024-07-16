from spkg_compose.cli.build import build
from spkg_compose.cli.args import Args
from spkg_compose.cli.help import help_cmd
from spkg_compose.cli.logger import logger
from spkg_compose.server import server_main
from spkg_compose.buildserver import build_server_main
from spkg_compose.utils.colors import *

args = Args()
args.parse_args()

try:
    command = args.get(1)
except IndexError:
    help_cmd()
    exit(0)


match args.args[1]:
    case "help":
        help_cmd()
    case "server":
        server_main(args.index_start(2))
    case "build-server":
        build_server_main(args.index_start(2))
    case "build":
        if len(args.args) < 3:
            print(f"{BACK_RED}  ERROR  {BACK_RESET}  Missing compose file!")
            exit(1)
        try:
            build(compose_file=args.args[2])
        except KeyboardInterrupt:
            print(f"{BACK_YELLOW} WARNING {BACK_RESET}  Canceling operation")
