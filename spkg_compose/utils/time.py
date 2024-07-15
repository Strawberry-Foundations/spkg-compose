import datetime


def unix_to_readable(unix_time):
    readable_time = datetime.datetime.fromtimestamp(unix_time).strftime('%Y-%m-%d %H:%M:%S')
    return readable_time
