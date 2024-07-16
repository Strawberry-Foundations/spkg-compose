from spkg_compose.utils.colors import *
from spkg_compose import VERSION


def help_cmd():
    print(f"""\
{BOLD}{CYAN}{UNDERLINE}spkg-compose v{VERSION}{CRESET}\n\
{GREEN}{BOLD}Usage:{RESET} {WHITE}spkg-compose {CYAN}[command] {RED}[<options>]{CRESET}\n\n\
{MAGENTA}{BOLD}Commands:{CRESET}
    {CYAN}{BOLD}build {RED}<composefile>:{CRESET} Builds a package by using the given compose file
    {CYAN}{BOLD}server:{CRESET} Starts a local spkg-compose server
    {CYAN}{BOLD}build-server:{CRESET} Starts a local spkg build server
    """)


"""
    {CYAN}{BOLD}compose:{CRESET} Starts one or more local proxies for the remote server using a configuration file
     {BOLD}↳ {MAGENTA}Options:{CRESET}
            {CYAN}{BOLD}-f, --file <secret>{CRESET}     Configuration file for proxy services   {GREEN}{BOLD}[default: service.yml]{CRESET}
"""
