import json
import tarfile


def create_package(metadata, source_dir, output_file):
    metadata_json = json.dumps(metadata).encode('utf-8')
    metadata_length = len(metadata_json)
    header = f"LENGTH={metadata_length}\n".encode('utf-8') + metadata_json

    with open(output_file, 'wb') as f:
        f.write(header)
        f.write(b'\n')

        with tarfile.open(fileobj=f, mode='w:gz') as tar:
            tar.add(source_dir, arcname='.')