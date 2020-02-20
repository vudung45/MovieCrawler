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
    if data.get("title"): #search by title
        try:
            movies = {}
            async for movie in AsyncMovieCollection.find({"title": {"$regex": f"(?i).*{data['title']}"}}):
                if movie.get("movieInstances"):
                    movies[str(movie["_id"])] = [await AsyncMovieInstanceCollection.find_one({"_id": ObjectId(instance_id)}) for instance_id in movie["movieInstances"]]
                    movies[str(movie["_id"])] = [item for item in movies[str(movie["_id"])] if item is not None] 

            return web.json_response({"status": 1, "response": json.loads(JSONEncoder().encode(movies))})  
                
        except Exception as e:
            return web.json_response({"status": 0,  "error": "Something went wrong!"})

    return web.json_response({"status": 0, "error": "Missing paramaters"})


@routes.get('/episodes')
async def search(request):
    data = request.query
    if data.get("movieId"):
        try:
            movie = await AsyncMovieCollection.find_one({"_id": ObjectId(data["movieId"])})
            if not movie:
                return web.json_response({"status": 0, "error": "movieID not found"})

            if not movie.get("movieInstances"):
                return web.json_response({"status": 1, "response": {}})

            instances_episodes = await asyncio.gather(*(get_episodes(instance_id, forceUpdate=data.get("force", False)) \
                                                        for instance_id in movie["movieInstances"]), return_exceptions=True)

            return web.json_response({"status": 1,  "response": dict(ChainMap(*(episodes for episodes in instances_episodes if not isinstance(episodes,Exception))))})   
        
        except Exception as e:
            print(e)
            return web.json_response({"status": 0,  "error": "Something went wrong!"})                
    
    elif data.get("instanceId"):
        return web.json_response({"status": 1,  "response": await get_episodes(data["instanceId"], forceUpdate=data.get("force", False))})   
    
    return web.json_response({"status": 0, "error": "Must provide an movieid or instanceid"})

async def get_episodes(instance_id, forceUpdate=False):
    movie_instance = await AsyncMovieInstanceCollection.find_one({"_id": ObjectId(instance_id)})
    if not movie_instance:
        return None

    if not movie_instance["watch_url"]:
        return None

    if not forceUpdate and movie_instance.get("lastEpisodeUpdate") \
            and float(movie_instance["lastEpisodeUpdate"]) + EPISODE_UPDATE_TTL > time.time():
        return { movie_instance["watch_url"] : movie_instance["episodes"] }
    
    watch_url = movie_instance["watch_url"]
    episodes = await MOVIE_PARSERS[movie_instance["origin"]].get_episodes_urls(watch_url)
    if len(episodes) > 0:
        print(await AsyncMovieInstanceCollection.find_one_and_update({"_id": ObjectId(instance_id)}, 
                                                                    {
                                                                        "$set": {
                                                                                    "episodes": episodes, 
                                                                                    "lastEpisodeUpdate": time.time()
                                                                                }
                                                                    }))
    return { movie_instance["watch_url"] : episodes }




if __name__ == "__main__":
    app = web.Application()
    app.add_routes(routes)
    web.run_app(app, port=os.getenv('PORT') or 8080)
    