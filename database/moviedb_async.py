import motor.motor_asyncio
from bson.objectid import ObjectId
from database.config import Config
import pymongo
from typing import Optional, Any, Dict
import copy
import string
import re
import asyncio

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
        "movieInstances": []
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
        
        return await self.find_one_and_update({"_id" : objectId}, update_query)

    async def create_new_movie(self, metadata) -> ObjectId:
        insertData =  {}
        for key in self.TEMPLATE:
            if key == "movieInstances":
                continue
            insertData[key] = metadata.get(key) 

        return (await self.insert_one(insertData)).inserted_id




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

        movie_title = instance["title"]
        movie_title = movie_title.translate(str.maketrans('', '', string.punctuation))

        words = re.findall(r"\w+", movie_title)

        matching_movie = await AsyncMovieCollection.find_one({
                "title": {
                  "$regex" : "(?i)" + ".*".join(words)
                }
            })

        return matching_movie


AsyncMovieInstanceCollection = AsyncMovieInstanceCollection()


async def assign_local_id():

    async for movie in AsyncMovieCollection.find({}):
        print(await asyncio.gather(*(
            AsyncMovieInstanceCollection.find_one_and_update({"_id": instance}, {"$set" : {
                "local_movie_id": movie["_id"]
            }}) for instance in movie["movieInstances"])))


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(assign_local_id())
