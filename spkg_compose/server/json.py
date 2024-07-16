import json


def convert_json_data(data):
    """Convert json data to python dict data"""
    return json.loads(data)


def send_json(data):
    """Convert python dict data to json"""
    return json.dumps(data)
