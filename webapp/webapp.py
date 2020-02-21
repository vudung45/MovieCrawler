import argparse
import khoaitv
import bilutv
from database.moviedb_async import AsyncMovieCollection, AsyncMovieInstanceCollection
from aiohttp import web, ClientSession
from bson.objectid import ObjectId
from utils.helper import JSONEncoder
import json
import asyncio
from collections import ChainMap
import time
import os


routes = web.RouteTableDef()

MOVIE_PARSERS = {
    khoaitv.config.Config.IDENTIFIER : khoaitv.parser.movie.MovieParser,
    bilutv.config.Config.IDENTIFIER : bilutv.parser.movie.MovieParser
}

EPISODE_UPDATE_TTL = 3600.0 # 1 hour


@routes.get('/search')
async def search(request):
    data = request.query
    print(data)
    if data.get("title"): #search by title
        try:
            limit = data.get("limit") ? data["limit"] : 20
            movies = await AsyncMovieCollection.find({"$or": [
                                    {"title_vietnamese": {"$regex": f"(?i).*{data['title']}"}}, 
                                    {"title": {"$regex": f"(?i).*{data['title']}"}}]}).to_list(length=limit)


            return web.json_response({"status": 1, "response": json.loads(JSONEncoder().encode(movies))})
        except Exception as e:
            print(e)
            return web.json_response({"status": 0,  "error": "Something went wrong!"}, status=500)

    return web.json_response({"status": 0, "error": "Missing paramaters"}, status=501)


@routes.get('/info')
async def getInstance(request):
    data = request.query
    try:
        if data.get("movieId"): #search by title
            try:
                movie_id = data["movieId"]
                movie = await AsyncMovieCollection.find_one({"_id": ObjectId(movie_id)});
                if not movie:
                    return web.json_response({"status": 0,  "error": "Movie not found!"}, status=501);

                return web.json_response({"status": 1, "response": json.loads(JSONEncoder().encode(movie))}) 
            except Exception as e:
                return web.json_response({"status": 0,  "error": "Something went wrong!"}, status=500);
        elif data.get("instanceId"):
            instance_id = data["instanceId"]
            instance = await AsyncMovieInstanceCollection.find_one({"_id": ObjectId(instance_id)});
            if not instance:
                return web.json_response({"status": 0,  "error": "instance_id not found!"}, status=501);

            return web.json_response({"status": 1, "response": json.loads(JSONEncoder().encode(instance))}) 
        else:
                return web.json_response({"status": 0,  "error": "Must provide movieId for instanceId"}, status=501)
    except Exception as e:
        print(e)
        return web.json_response({"status": 0,  "error": "Something went wrong!"}, status=500) 


@routes.get('/episodes')
async def search(request):
    data = request.query
    try:
        if data.get("movieId"):
                movie = await AsyncMovieCollection.find_one({"_id": ObjectId(data["movieId"])})
                if not movie:
                    return web.json_response({"status": 0, "error": "movieID not found"}, status=501)

                if not movie.get("movieInstances"):
                    return web.json_response({"status": 1, "response": {}})

                instances_episodes = await asyncio.gather(*(get_episodes(instance_id, forceUpdate=data.get("force", False)) \
                                                            for instance_id in movie["movieInstances"]), return_exceptions=True)

                return web.json_response({"status": 1,  
                                         "response": dict(ChainMap(*(episodes for episodes 
                                                                     in instances_episodes if not isinstance(episodes,Exception))))})   
            
        elif data.get("instanceId"):
            return web.json_response({"status": 1,  "response": await get_episodes(data["instanceId"], forceUpdate=data.get("force", False))}) 

        return web.json_response({"status": 0, "error": "Must provide an movieid or instanceid"}, status=501)
        
    except Exception as e:
                print(e)
                return web.json_response({"status": 0,  "error": "Something went wrong!"}, status=500)  
    

async def get_episodes(instance_id, forceUpdate=False):
    movie_instance = await AsyncMovieInstanceCollection.find_one({"_id": ObjectId(instance_id)})
    if not movie_instance:
        raise Exception("instance_id not found")

    if not movie_instance["watch_url"]:
        return {str(movie_instance["_id"]) : { "origin" : movie_instance["origin"], "episodes": []}}

    if not forceUpdate and movie_instance.get("lastEpisodeUpdate") \
            and float(movie_instance["lastEpisodeUpdate"]) + EPISODE_UPDATE_TTL > time.time():
        return { str(movie_instance["_id"]) : { "origin" : movie_instance["origin"], "episodes": movie_instance["episodes"]}}
    
    watch_url = movie_instance["watch_url"]
    episodes = await MOVIE_PARSERS[movie_instance["origin"]].get_episodes_urls(watch_url)
    print(episodes)
    if len(episodes) > 0:
        print(await AsyncMovieInstanceCollection.find_one_and_update({"_id": ObjectId(instance_id)}, 
                                                                    {
                                                                        "$set": {
                                                                                    "episodes": episodes, 
                                                                                    "lastEpisodeUpdate": time.time()
                                                                                }
                                                                    }))
    return { str(movie_instance["_id"]) : { "origin" : movie_instance["origin"], "episodes": episodes}}



if __name__ == "__main__":
    app = web.Application()
    app.add_routes(routes)
    web.run_app(app, port=os.getenv('PORT') or 5002)
    