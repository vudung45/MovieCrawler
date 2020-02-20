from database.moviedb_async import AsyncMovieCollection, AsyncMovieInstanceCollection
from bilutv.parser.general import GeneralParser
from bilutv.parser.movie import MovieParser
from custom_request.request import AsyncSession
from utils.helper import chunk_iterator
from bilutv.config import Config
import asyncio


class BiluTV:

    @classmethod
    async def populate(cls, debug=False):
        categories = await GeneralParser.get_categories_page(debug=debug)
        categorized_movies_urls, total_links =  await GeneralParser.get_categorized_movie_urls(categories, debug=debug)
        movies_urls = {url for movies_urls in categorized_movies_urls.values() for url in movies_urls}
        print(f"Total links: {len(movies_urls)}")

        async def _update_db_wrapper(metadata):
            
            # merge all instances of the same movie on different sites into one main instance
            # create the main movie instance if not exists
            matching_movie = await AsyncMovieInstanceCollection.findCorrespondingMovie(instance=metadata)
            movie_object_id = None
            if not matching_movie:
                movie_object_id = await AsyncMovieCollection.create_new_movie({"title": metadata["title"]})
            else:
                movie_object_id = matching_movie["_id"]

            if not movie_object_id:
                return

            # check if we have already added this movie
            existing_instance = await AsyncMovieInstanceCollection.find_one({"movie_id": metadata["movie_id"]})
            metadata["local_movie_id"] = movie_object_id # we use this to serve our purpuses locally
            instance_object_id = None
            if not existing_instance:
                instance_object_id = (await AsyncMovieInstanceCollection.insert_one(metadata)).inserted_id
                if debug:
                    print(f"Inserting new object {instance_object_id}" )
            else:
                instance_object_id = existing_instance["_id"]
                if debug:
                    print(f"Updating object {instance_object_id}")

            await AsyncMovieCollection.add_movie_instance(movie_object_id, instance_object_id)

        async def _routine_wrapper(url, session):
            movieMetadata = []
            metadata = None
            try:
                metadata = await MovieParser.get_movie_info(url, debug=debug, session=session)
            except Exception as e:
                if debug:
                    print(e)
                return

            if metadata and "movie_id" in metadata and metadata["movie_id"]:
                await _update_db_wrapper(metadata)


        # process 20 urls at a time to avoid 500 http error
        for urls_range in chunk_iterator(movies_urls, 20):
            session = AsyncSession()
            await asyncio.gather(*(_routine_wrapper(url, session) for url in urls_range), return_exceptions=True)
            await session.close()

    @classmethod
    async def mergeMovies(cls, debug=False):
        for instance in MovieInstanceCollection.find({"origin" : Config.IDENTIFIER}):
            matching_movie = MovieInstanceCollection.findCorrespondingMovie(instance["_id"])
            movie_object_id = None
            if not matching_movie:
                movie_object_id = MovieCollection.create_new_movie({"title": instance["title"]})
            else:
                movie_object_id = matching_movie["_id"]

            if debug:
                print(MovieCollection.add_movie_instance(movie_object_id, instance["_id"]))

if __name__ == "__main__":
    eloop = asyncio.get_event_loop()
    metadata = eloop.run_until_complete(BiluTV.populate(debug=True))
    #eloop.run_until_complete(KhoaiTV.mergeMovies(debug=True))








        
        
