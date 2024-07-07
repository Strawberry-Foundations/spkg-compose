from binpkg.metadata import Metadata

import json
import tarfile


class BinPkg:
    def __init__(self, meta: Metadata, source: str, output: str):
        self.meta: Metadata = meta
        self.source: str = source
        self.output: str = output

    @classmethod
    def create(cls, meta: Metadata, source_dir: str, output_file: str):
        metadata_json = json.dumps(meta.serialize()).encode('utf-8')
        metadata_length = len(metadata_json)
        header = f"LENGTH={metadata_length}\n".encode('utf-8') + metadata_json

        with open(output_file, 'wb') as f:
            f.write(header)
            f.write(b'\n')

            with tarfile.open(fileobj=f, mode='w:gz') as tar:
                tar.add(source_dir, arcname='.')

        return cls(meta, source_dir, output_file)

    @classmethod
    def read(cls, input_file: str):
        with open(input_file, 'rb') as f:
            length_line = f.readline().strip()
            metadata_length = int(length_line.split(b'=')[1])

            metadata_json = f.read(metadata_length)
            meta = json.loads(metadata_json.decode('utf-8'))

        return cls(
            meta=Metadata.from_json(meta),
            source=input_file,
            output=None
        )

    @classmethod
    def extract(cls, input_file: str, output_dir: str):
        with open(input_file, 'rb') as f:
            length_line = f.readline().strip()
            metadata_length = int(length_line.split(b'=')[1])

            metadata_json = f.read(metadata_length)
            meta = json.loads(metadata_json.decode('utf-8'))

            f.read(1)

            with tarfile.open(fileobj=f, mode='r:gz') as tar:
                tar.extractall(path=output_dir)

        return cls(
            meta=Metadata.from_json(meta),
            source=input_file,
            output=output_dir
        )

    def self_extract(self, output_dir: str):
        with open(str(self.source), 'rb') as f:
            length_line = f.readline().strip()
            metadata_length = int(length_line.split(b'=')[1])

            metadata_json = f.read(metadata_length)
            _ = json.loads(metadata_json.decode('utf-8'))

            f.read(1)

            with tarfile.open(fileobj=f, mode='r:gz') as tar:
                tar.extractall(path=output_dir)
