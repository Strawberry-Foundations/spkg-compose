def extract_path(url):
    trimmed_url = url.split('/main')[1]
    path_with_main = "/main" + "/".join(trimmed_url.split('/')[:-1])
    return path_with_main
