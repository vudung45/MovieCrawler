import json

class Config:
    LOGIN_CREDENTIALS = ""


with open("./credentials/mongodb.json", "r") as f:
    settings = json.loads(f.read())
    Config.LOGIN_CREDENTIALS = settings["loginURL"]