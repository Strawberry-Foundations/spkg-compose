from spkg_compose.utils.colors import *
from enum import Enum
from datetime import datetime


def current_time(time_fmt: str) -> str:
    local = datetime.now()
    return local.strftime(time_fmt)


class LogFormat:
    def __init__(self):
        self.info = f"{C_RESET}{BOLD}[%<time>%] {GREEN}[%<levelname>%]{C_RESET}    [%<message>%]"
        self.ok = f"{C_RESET}{BOLD}[%<time>%] {BLUE}[%<levelname>%]{C_RESET}      [%<message>%]"
        self.error = f"{C_RESET}{BOLD}[%<time>%] {RED}[%<levelname>%]{C_RESET}   [%<message>%]"
        self.default = f"{C_RESET}{BOLD}[%<time>%] {CYAN}INIT{C_RESET}    [%<message>%]"
        self.warning = f"{C_RESET}{BOLD}[%<time>%] {YELLOW}[%<levelname>%]{C_RESET} [%<message>%]"
        self.critical = f"{C_RESET}{BOLD}[%<time>%] {YELLOW}[%<levelname>%]{C_RESET} [%<message>%]"
        self.panic = f"{C_RESET}{BOLD}[%<time>%] {RED}[%<levelname>%]{C_RESET}   [%<message>%]"
        self.routine = f"{C_RESET}{BOLD}[%<time>%] {MAGENTA}[%<levelname>%]{C_RESET} [%<message>%]"
        self.time_fmt = "%Y-%m-%d %H:%M:%S"


class LogLevel(Enum):
    DEFAULT = 0
    INFO = 1
    ERROR = 2
    WARNING = 3
    CRITICAL = 4
    PANIC = 5
    OK = 6
    ROUTINE = 7


class Logger:
    def __init__(self):
        self.formatting = LogFormat()

    def parse(self, level: LogLevel, content: str) -> str:
        match level:
            case LogLevel.DEFAULT:
                return self.formatting.default \
                    .replace("[%<levelname>%]", level.name) \
                    .replace("[%<message>%]", content) \
                    .replace("[%<time>%]", current_time(self.formatting.time_fmt))
            case LogLevel.OK:
                return self.formatting.ok \
                    .replace("[%<levelname>%]", level.name) \
                    .replace("[%<message>%]", content) \
                    .replace("[%<time>%]", current_time(self.formatting.time_fmt))
            case LogLevel.INFO:
                return self.formatting.info \
                    .replace("[%<levelname>%]", level.name) \
                    .replace("[%<message>%]", content) \
                    .replace("[%<time>%]", current_time(self.formatting.time_fmt))
            case LogLevel.ERROR:
                return self.formatting.error \
                    .replace("[%<levelname>%]", level.name) \
                    .replace("[%<message>%]", content) \
                    .replace("[%<time>%]", current_time(self.formatting.time_fmt))
            case LogLevel.WARNING:
                return self.formatting.warning \
                    .replace("[%<levelname>%]", level.name) \
                    .replace("[%<message>%]", content) \
                    .replace("[%<time>%]", current_time(self.formatting.time_fmt))
            case LogLevel.CRITICAL:
                return self.formatting.critical \
                    .replace("[%<levelname>%]", level.name) \
                    .replace("[%<message>%]", content) \
                    .replace("[%<time>%]", current_time(self.formatting.time_fmt))
            case LogLevel.PANIC:
                return self.formatting.panic \
                    .replace("[%<levelname>%]", level.name) \
                    .replace("[%<message>%]", content) \
                    .replace("[%<time>%]", current_time(self.formatting.time_fmt))
            case LogLevel.ROUTINE:
                return self.formatting.routine \
                    .replace("[%<levelname>%]", level.name) \
                    .replace("[%<message>%]", content) \
                    .replace("[%<time>%]", current_time(self.formatting.time_fmt))

    def default(self, log_message: str):
        print(self.parse(LogLevel.DEFAULT, log_message))

    def ok(self, log_message: str):
        print(self.parse(LogLevel.OK, log_message))

    def info(self, log_message: str):
        print(self.parse(LogLevel.INFO, log_message))

    def error(self, log_message: str):
        print(self.parse(LogLevel.ERROR, log_message))

    def warning(self, log_message: str):
        print(self.parse(LogLevel.WARNING, log_message))

    def critical(self, log_message: str):
        print(self.parse(LogLevel.CRITICAL, log_message))

    def panic(self, log_message: str):
        print(self.parse(LogLevel.PANIC, log_message))

    def routine(self, log_message: str):
        print(self.parse(LogLevel.ROUTINE, log_message))

logger = Logger()
