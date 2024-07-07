def remove_double_slash(line):
    protocols = ["http://", "https://", "ftp://", "file://", "ssh://", "sftp://"]

    for protocol in protocols:
        if line.startswith(protocol):
            return line

    parts = line.split("//", 1)
    if len(parts) > 1:
        return parts[0]
    else:
        return line


def read(file_path):
    data = {}

    with open(file_path, 'r') as file:
        section = None

        for line in file:
            line = line.strip()

            if line.startswith('[') and line.endswith(']'):
                section = line[1:-1]
                data[section] = {}

            elif section:
                if line.startswith('[') and line.endswith(']') or not line.strip():
                    continue

                key, value = line.split('=', 1)
                value = remove_double_slash(value)

                data[section][key.strip()] = value.strip()

    return data