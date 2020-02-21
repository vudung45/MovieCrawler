import json
import os
class Config:
    LOGIN_CREDENTIALS = os.environ.get("MONGOURI")


try:
    with open("./credentials/mongodb.json", "r") as f:
        settings = json.loads(f.read())
        Config.LOGIN_CREDENTIALS = settings["loginURL"]
except Exception as e:
    print(e)
