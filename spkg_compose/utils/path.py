def extract_path(url):
    trimmed_url = url.split('/main')[1]
    path_without_filename = "/".join(trimmed_url.split('/')[:-1])
    return path_without_filename
