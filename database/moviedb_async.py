import motor.motor_asyncio
from bson.objectid import ObjectId
from database.config import Config
import pymongo
from typing import Optional, Any, Dict
import copy
import string
import re
import asyncio
from pymongo import ReturnDocument
from utils.helper import no_accent_vietnamese

client = motor.motor_asyncio.AsyncIOMotorClient(Config.LOGIN_CREDENTIALS)
MOVIES_DB = client["movies_db"]




class FakeAsyncCollection:# a work around because some reason I can't extends AsyncIOMotorCollection class

    def __init__(self, db, name):
        for method_name in (method_name for method_name in dir(db[name])
                      if callable(getattr(db[name], method_name)) and not method_name.startswith('__')):
            exec('self.%s = client["movies_db"]["movies"].%s' % (method_name, method_name))

class AsyncMovieCollection(motor.motor_asyncio.AsyncIOMotorCollection):

    TEMPLATE =  {
        "title": None,
        "title_vietnamese": None,
        "title_vietnamese_noaccent": None,
        "aliases": [],
        "movieInstances": [],
        "image": None,
        "year": None
    }

    def __init__(self):
        """Calling __init__ of parent class is failing for some reason"""

    def __new__(cls):
        collection = motor.motor_asyncio.AsyncIOMotorCollection(MOVIES_DB, "movies")
        collection.__class__ = AsyncMovieCollection
        return collection


    async def add_movie_instance(self, objectId, movieInstanceId: str) -> Optional[Dict[Any, Any]]: 
        if(type(objectId) == str):
            objectId = ObjectId(objectId)

        if(type(movieInstanceId) == str):
            movieInstanceId  = ObjectId(movieInstanceId)

        update_query = {
                "$addToSet": {
                    "movieInstances": movieInstanceId
                }
        }
        
        return await self.find_one_and_update({"_id" : objectId}, update_query, return_document=ReturnDocument.AFTER)

    def generateTemplate(self, metadata):
        insertData =  {}
        for key in self.TEMPLATE:
            if key == "movieInstances":
                continue
            insertData[key] = metadata.get(key)
        if insertData.get("title_vietnamese"):
            insertData["title_vietnamese_noaccent"] = no_accent_vietnamese(insertData["title_vietnamese"])
        return insertData

    async def create_new_movie(self, metadata) -> ObjectId:
        insertData =  {}
        for key in self.TEMPLATE:
            if key == "movieInstances":
                continue
            insertData[key] = metadata.get(key)

        return (await self.find_one_and_update(insertData, insertData, upsert=True))["_id"]




AsyncMovieCollection = AsyncMovieCollection()


class AsyncMovieInstanceCollection(motor.motor_asyncio.AsyncIOMotorCollection): # multiple MovieInstance could be mapped to a single movie
    def __init__(self):
        """Calling __init__ of parent class is failing for some reason"""

    def __new__(cls):
        collection = motor.motor_asyncio.AsyncIOMotorCollection(MOVIES_DB, "instances")
        collection.__class__ = AsyncMovieInstanceCollection
        return collection


    async def findCorrespondingMovie(self, objectId=None, instance=None) -> Optional[Dict[Any, Any]]:
        if not instance: 
            if(type(objectId) == str):
                objectId = ObjectId(objectId)

            instance = await self.find_one({ "_id": objectId })

        objectId = instance["_id"]


        movie_title = instance["title"]
        movie_title = movie_title.translate(str.maketrans('', '', string.punctuation))

        movie_vtitle = instance["title_vietnamese"]
        movie_vtitle = movie_vtitle.translate(str.maketrans('', '', string.punctuation))

        words = re.findall(r"\w+", movie_title)
        vwords = re.findall(r"\w+", movie_vtitle)

        matching_movie = await AsyncMovieCollection.find_one({ 
                            "$or": [ 
                                        {"title_vietnamese": {
                                          "$regex" : "(?i)^\W*" + "\W+".join(vwords) + "\W*$"
                                        }}, 
                                        {"title": {
                                          "$regex" : "(?i)^\W*" + "\W+".join(words) + "\W*$"
                                        }}
                                    ]
                        })

        return matching_movie

    async def mergeWithCorrespondingMovie(self, objectId=None, instance=None) -> Dict[Any, Any]:
        if not instance: 
            if(type(objectId) == str):
                objectId = ObjectId(objectId)

            instance = await self.find_one({ "_id": objectId })

        objectId = instance["_id"]

        movie_title = instance["title"] if instance.get("title") else instance["title_vietnamese"]
        movie_title = movie_title.translate(str.maketrans('', '', string.punctuation))

        movie_vtitle = instance["title_vietnamese"]
        movie_vtitle = movie_vtitle.translate(str.maketrans('', '', string.punctuation))

        words = re.findall(r"(?i)[a-z]+", movie_title)
        vwords = re.findall(r"(?i)[a-z]+", movie_vtitle)

        optional_predicate = {"year": instance["year"]} if instance.get("year") else {}
        matching_movie = await AsyncMovieCollection.find_one_and_update(
            {"$and" : 
                [
                    { 
                        "aliases": {
                            "$regex": "(?i)" + "[^a-zA-Z]+".join(vwords)+"|"+"(?i)" + "[^a-zA-Z]+".join(words),
                            "$options": "i"
                        }
                    }, 
                    optional_predicate
                ]
            }, {
                "$addToSet" : {
                                    "aliases" :  { "$each" : [movie_title, movie_vtitle] },
                                    "movieInstances": instance["_id"]
                            }
        
            },
            upsert=True,
            return_document=ReturnDocument.AFTER
        )
        movie_template = AsyncMovieCollection.generateTemplate(instance)
        missing_template = { k: movie_template[k] for k in movie_template if k not in matching_movie}

        if len(missing_template):
            matching_movie = await AsyncMovieCollection.find_one_and_update({"_id" : matching_movie["_id"]}, 
                                                  {"$set" : missing_template}, return_document=ReturnDocument.AFTER)

        return matching_movie


AsyncMovieInstanceCollection = AsyncMovieInstanceCollection()


async def assign_local_id():
    movies = await AsyncMovieCollection.find({}).to_list(length=None)

    print(await asyncio.gather(*(
        AsyncMovieInstanceCollection.find_one_and_update({"_id": instance}, {"$set" : {
            "local_movie_id": movie["_id"]
        }}) for movie in movies for instance in movie["movieInstances"])))

async def delete_origin(origin):
    movies = await AsyncMovieCollection.find({}).to_list(length=None)

    print(await asyncio.gather(*(
        AsyncMovieInstanceCollection.find_one_and_update({"_id": instance}, {"$set" : {
            "local_movie_id": movie["_id"]
        }}) for movie in movies for instance in movie["movieInstances"])))


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(assign_local_id())
