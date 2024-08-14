from spkg_compose.cli.build import build
from spkg_compose.cli.args import Args
from spkg_compose.cli.help import help_cmd
from spkg_compose.cli.logger import logger
from spkg_compose.utils.colors import *

import sys

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
        from spkg_compose.server import server_main
        server_main(args.index_start(2))

    case "build-server":
        from spkg_compose.buildserver import build_server_main
        build_server_main(args.index_start(2))

    case "repo-api":
        from spkg_compose.http.repo import repo_api_main
        repo_api_main()

    case "build":
        if len(args.args) < 3:
            print(f"{BACK_RED}  ERROR  {BACK_RESET}  Missing compose file!")
            exit(1)
        try:
            build(compose_file=args.args[2])
        except KeyboardInterrupt:
            print(f"{BACK_YELLOW} WARNING {BACK_RESET}  Canceling operation")

    case _:
        print(f"{BACK_RED}  ERROR  {BACK_RESET}  Invalid command!")
        sys.exit(1)
