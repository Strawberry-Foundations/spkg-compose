import datetime


def unix_to_readable(unix_time):
    readable_time = datetime.datetime.fromtimestamp(unix_time).strftime('%Y-%m-%d %H:%M:%S')
    return readable_time


def convert_time(elapsed_time):
    if elapsed_time < 1:
        time_str = f"{elapsed_time * 1000:.2f} ms"
    elif elapsed_time < 60:
        time_str = f"{elapsed_time:.2f} s"
    elif elapsed_time < 3600:
        minutes, seconds = divmod(elapsed_time, 60)
        time_str = f"{int(minutes)} m {seconds:.2f} s"
    else:
        hours, remainder = divmod(elapsed_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        time_str = f"{int(hours)} h {int(minutes)} m {seconds:.2f} s"

    return time_str