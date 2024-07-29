def extract_path(url):
    trimmed_url = url.split('/packages')[1]
    path_without_filename = "/".join(trimmed_url.split('/')[:-1])
    return path_without_filename


def extract_base_url(url):
    trimmed_url = url.split('/main')[0]
    return trimmed_url


def extract_base_path(url):
    trimmed_url = "/".join(url.split('/')[:-1])
    return trimmed_url
