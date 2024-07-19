from spkg_compose.server.config import config
from flask import Flask, request, abort

app = Flask(__name__)


@app.route('/upload', methods=['POST'])
def upload_file():
    auth_header = request.headers.get('Authorization')

    if auth_header not in [f"Bearer {token}" for token in config.repo_api.allowed_tokens]:
        abort(403)

    if 'file' not in request.files:
        abort(400, "No file part")

    file = request.files['file']
    if file.filename == '':
        abort(400, "No selected file")

    file.save(f"./uploads/{file.filename}")
    return "File uploaded successfully", 200


def repo_api_main():
    app.run(
        host=config.repo_api.address,
        port=config.repo_api.port,
        threaded=True,
        debug=True
    )
