import pymongo
from bson.objectid import ObjectId
from database.config import Config
import string
import re
from typing import Dict, Any

client = pymongo.MongoClient(Config.LOGIN_CREDENTIALS, connectTimeoutMS=30000)
MOVIES_DB = client.get_database("movies_db")


class MovieCollection(pymongo.collection.Collection):

    TEMPLATE =  {
        "title": None,
        "title_vietnamese": None,
        "movieInstances": []
    }
    def __init__(self):
        super().__init__(MOVIES_DB, "movies")

    def add_movie_instance(self, objectId, movieInstanceId: str) -> Dict[Any, Any]: 
        if(type(objectId) == str):
            objectId = ObjectId(objectId)

        if(type(movieInstanceId) == str):
            movieInstanceId  = ObjectId(movieInstanceId)

        update_query = {
                "$addToSet": {
                    "movieInstances": movieInstanceId
                }
        }
        
        return self.find_one_and_update({"_id" : objectId}, update_query)

    def create_new_movie(self, metadata) -> ObjectId:
        insertData =  {}
        for key in self.TEMPLATE:
            if key == "movieInstances":
                continue
            insertData[key] = metadata.get(key) 

        return self.insert_one(insertData).inserted_id




MovieCollection = MovieCollection()


class MovieInstanceCollection(pymongo.collection.Collection): # multiple MovieInstance could be mapped to a single movie
    def __init__(self):
       super().__init__(MOVIES_DB, "instances")

    def findCorrespondingMovie(self, objectId):
        if(type(objectId) == str):
            objectId = ObjectId(objectId)

        instance = self.find_one({ "_id": objectId })
        movie_title = instance["title"]
        movie_title = movie_title.translate(str.maketrans('', '', string.punctuation))

        words = re.findall(r"\w+", movie_title)

        matching_movie = MovieCollection.find_one({
                "title": {
                  "$regex" : "(?i)^\W*" + "\W+".join(words) + "\W*$"
                }
            })

        return matching_movie


MovieInstanceCollection = MovieInstanceCollection()

