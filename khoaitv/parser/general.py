from khoaitv.config import Config
from custom_request.request import AsyncRequest
from bs4 import BeautifulSoup
import typing
import time

class GeneralParser:

    @classmethod
    async def get_categories_page(cls, debug=False):
        links = []
        try:
            body, request_info = await AsyncRequest.get(Config.BASE_URL)
            html_parser = BeautifulSoup(body, "html.parser")
            categories = html_parser.find("div", {"id": "bs-example-navbar-collapse-1"}).find("ul").find("li").find("ul")
            for category in categories.findAll("li"):
                links.append(category.find("a")["href"])
        except Exception as e:
            if debug:
                print(repr(e))
        return links

    @classmethod
    async def get_movie_urls(cls, category_url, debug=False):
        def get_num_pages(content):
            n_pages = 1
            try:
                html_parser = BeautifulSoup(content, "html.parser")
                page_last = html_parser.find("li", class_="pag-last").find("a")["href"]
                # http://khoaitv.org/the-loai/chien-tranh/page/44
                n_pages = int(page_last.split("/")[-1])
            except Exception as e:
                if debug:
                    print(f"get_num_pages()\n{repr(e)}")
            return n_pages

        async def parse_urls_from_page(page_url, session=None, debug=False):
            """
            get movie urls from a page
            """
            n_pages = 0
            links = []
            try:
                body, request_info = await AsyncRequest.get(page_url, delay=Config.REQUEST_DELAY, session=session)
                if(not body):
                    return links
                html_parser = BeautifulSoup(body, "html.parser")
                for film_box in html_parser.findAll("a", class_="film-small"):
                    links.append(film_box["href"])
                if debug:
                    print(links)
                return links;
            except Exception as e:
                if debug:
                    print("parse_urls_from_page()", repr(e))
            return links

        links = []
        try:
            # use the same session to concurrently call urls from KhoaiTV page
            async with AsyncRequest.new_session() as session:
                body, request_info = await AsyncRequest.get(category_url, delay=Config.REQUEST_DELAY, session=session)
                num_pages = get_num_pages(body)
                parse_routines = await asyncio.gather(*( \
                        parse_urls_from_page(Config.CATEGORY_PAGINATION_URL.format(category_url=category_url, page=page), debug=debug, session=session) \
                                 for page in range(1, num_pages+1)), return_exceptions=True)
                for routine in parse_routines:
                    if type(routine) == Exception:
                        if debug:
                            print(repr(routine))
                        continue
                    # routine should be of type list
                    links += routine 
        except Exception as e:
            if debug:
                print(repr(e))
        return links

    @classmethod
    async def get_categorized_movie_urls(cls, category_urls, debug=False):
        categorized_movies = {}
        # parse_routines = await asyncio.gather(*( \
        #         cls.get_movie_urls(url) \
        #             for url in category_urls), return_exceptions=True)
        total = 0
        for category in category_urls:
            categorized_movies[category] = await cls.get_movie_urls(category, debug=debug)
            total += len(categorized_movies[category])

        return categorized_movies, total


if __name__ == "__main__":
    import asyncio
    eloop = asyncio.new_event_loop()
    start = time.time()
    categories = eloop.run_until_complete(GeneralParser.get_categories_page(debug=True))
    categorized_movies_urls, total_links = eloop.run_until_complete(GeneralParser.get_categorized_movie_urls(categories, debug=True))
    print(f"Parsing completed in {time.time() - start} seconds. "
          f"Total of {total_links} links.")



