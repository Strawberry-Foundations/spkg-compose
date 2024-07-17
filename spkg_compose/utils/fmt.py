from spkg_compose.utils.colors import *


def calculate_percentage(total, value):
    """Calculate the percentage of value from total and return colored output."""
    if total == 0:
        return "Total can't be zero"

    percentage = (value / total) * 100

    if percentage > 60:
        color = GREEN
    elif percentage > 30:
        color = YELLOW
    else:
        color = RED

    reset_color = "\033[0m"
    return f"{color}{value} ({percentage:.2f}%) {reset_color}"
