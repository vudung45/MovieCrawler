
from database.moviedb_async import AsyncMovieCollection, AsyncMovieInstanceCollection
from motphim.parser.general import GeneralParser
from motphim.parser.movie import MovieParser
from custom_request.request import AsyncSession
from utils.helper import chunk_iterator
import asyncio
from motphim.config import Config
from pymongo import ReturnDocument


class Motphim:

    @classmethod
    async def populate(cls, debug=False):
        categories = await GeneralParser.get_categories_page(debug=debug)
        categorized_movies_urls, total_links =  await GeneralParser.get_categorized_movie_urls(categories, debug=debug)
        movies_urls = {url for movies_urls in categorized_movies_urls.values() for url in movies_urls}
        print(f"Total links: {len(movies_urls)}")

        async def _update_db_wrapper(metadata):
             # check if we have already added this movie 
            try:
                instance = await AsyncMovieInstanceCollection.find_one_and_update({"origin": Config.IDENTIFIER, "movie_id": metadata["movie_id"]}, 
                                                                                  {"$set": metadata},
                                                                                  upsert=True, 
                                                                                  return_document=ReturnDocument.AFTER)

                # merge all instances of the same movie on different sites into one main instance
                # create the main movie instance if not exists
                matching_movie = await AsyncMovieInstanceCollection.mergeWithCorrespondingMovie(instance=instance)
                movie_object_id = matching_movie["_id"]
                print(movie_object_id)
            except Exeption as e:
                if debug:
                    print(e)
    
        async def _routine_wrapper(url, session):
            movieMetadata = []
            metadata = None
            try:
                metadata = await MovieParser.get_movie_info(url, debug=debug, session=session)
            except Exception as e:
                if debug:
                    print(e)
                return
           # print(metadata)
            await _update_db_wrapper(metadata)


        # process 20 urls at a time to avoid 500 http error
        for urls_range in chunk_iterator(movies_urls, 20):
            session = AsyncSession()
            await asyncio.gather(*(_routine_wrapper(url, session) for url in urls_range), return_exceptions=True)
            await session.close()

    @classmethod
    async def mergeMovies(cls, debug=False):
        instances =  await AsyncMovieInstanceCollection.find({"origin" : Config.IDENTIFIER}).to_list(length=None)
        if debug:
            print(instances)
        # stop = False
        async def _routine(instance):
            # merge all instances of the same movie on different sites into one main instance
            # create the main movie instance if not exists
            if debug:
                print(f"Finding matching movie for instance: {str(instance)}")
            matching_movie = await AsyncMovieInstanceCollection.mergeWithCorrespondingMovie(instance=instance)
            print(matching_movie)

        await asyncio.gather(*(_routine(instance) for instance in instances))

if __name__ == "__main__":
    eloop = asyncio.get_event_loop()
    metadata = eloop.run_until_complete(Motphim.populate(debug=True))
    #eloop.run_until_complete(Motphim.mergeMovies(debug=True))








        
        
