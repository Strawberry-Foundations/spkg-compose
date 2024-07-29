from spkg_compose.server.config import config
from spkg_compose import init_dir

from flask import Flask, request, abort

import json


app = Flask(__name__)

with open(f"{init_dir}/data/index.json", 'r') as json_file:
    index = json.load(json_file)


@app.route('/upload', methods=['POST'])
def upload_file():
    auth_header = request.headers.get('Authorization')
    package_name = request.headers.get('Package')

    if auth_header not in [f"Bearer {token}" for token in config.repo_api.allowed_tokens]:
        abort(403)

    if 'file' not in request.files:
        abort(400, "No file part")

    file = request.files['file']
    if file.filename == '':
        abort(400, "No selected file")

    try:
        file.save(f"{init_dir}/local_repo/{index[package_name]['binpkg_path']}/{file.filename}")
    except Exception as err:
        return f"Package not found ({err})", 404

    return f"Binpkg for package '{package_name}' uploaded successfully ({file.filename})", 200


def repo_api_main():
    app.run(
        host=config.repo_api.address,
        port=config.repo_api.port,
        threaded=True,
        debug=True
    )
