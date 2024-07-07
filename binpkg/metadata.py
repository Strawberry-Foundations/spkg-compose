class Metadata:
    def __init__(self, name: str, id: str, version: str, description: str, architecture: str, author: str):
        self.name = name
        self.id = id
        self.version = version
        self.description = description
        self.architecture = architecture
        self.author = author

    @classmethod
    def from_json(cls, json: dict):
        name = json["name"]
        id = json["id"]
        version = json["version"]
        description = json["description"]
        architecture = json["architecture"]
        author = json["author"]

        return cls(name, id, version, description, architecture, author)

    def serialize(self):
        return {
            "name": self.name,
            "id": self.id,
            "version": self.version,
            "description": self.description,
            "architecture": self.architecture,
            "author": self.author,
        }
