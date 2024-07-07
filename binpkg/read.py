import json
import tarfile


def extract_package(input_file, output_dir):
    with open(input_file, 'rb') as f:
        length_line = f.readline().strip()
        metadata_length = int(length_line.split(b'=')[1])

        metadata_json = f.read(metadata_length)
        metadata = json.loads(metadata_json.decode('utf-8'))

        f.read(1)

        with tarfile.open(fileobj=f, mode='r:gz') as tar:
            tar.extractall(path=output_dir)

    return metadata


def read_metadata(input_file):
    with open(input_file, 'rb') as f:
        length_line = f.readline().strip()
        metadata_length = int(length_line.split(b'=')[1])

        metadata_json = f.read(metadata_length)
        metadata = json.loads(metadata_json.decode('utf-8'))

    return metadata