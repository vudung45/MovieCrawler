from khoaitv.config import Config
from utils.helper import normalize_url
from custom_request.request import AsyncSession, AsyncRequest
from bs4 import BeautifulSoup
import typing
import time

def _get_num_pages(content, debug=False):
            n_pages = 1
            try:
                html_parser = BeautifulSoup(content, "html.parser")
                page_last = html_parser.find("li", class_="pag-last").find("a")["href"]
                # https://vuviphimmoi.com/anime/page/1
                n_pages = int(page_last.split("/")[-1])
            except Exception as e:
                if debug:
                    print(f"_get_num_pages()\n{repr(e)}")
            return n_pages

def _parse_urls_from_page(content, debug=False):
    """
    get movie urls from a page
    """
    n_pages = 0
    links = []
    try:
        html_parser = BeautifulSoup(content, "html.parser")
        for film_box in html_parser.findAll("a", class_="film-small"):
            links.append(film_box["href"])
        return links;
    except Exception as e:
        if debug:
            print("_parse_urls_from_page()", repr(e))
    return links


class GeneralParser:

    @classmethod
    async def get_categories_page(cls, debug=False):
        links = []
        try:
            async with AsyncSession() as session:
                res = await session.get(Config.BASE_URL)
                res.raise_for_status()
                html_parser = BeautifulSoup(await res.text(), "html.parser")
                categories = html_parser.find("div", {"id": "bs-example-navbar-collapse-1"}).find("ul").find("li").find("ul")
                for category in categories.findAll("li"):
                    links.append(category.find("a")["href"])
        except Exception as e:
            if debug:
                print(f"get_categories_page() {repr(e)}")
        return links

    @classmethod
    async def get_movie_urls(cls, category_url, session=None, debug=False):
        create_session = session is None
        # if a session is not provided then we create one
        if not session:
            session = AsyncSession()

        movie_urls = []
        body, request_info = await AsyncRequest.get(category_url, delay=Config.REQUEST_DELAY, session=session)
        num_pages = _get_num_pages(body)
        pages_content = [body] # first page is already parsed

        # all page links except the first page
        page_links = [Config.CATEGORY_PAGINATION_URL.format(\
                            category_url=normalize_url(category_url), page=page) 
                                for page in range(2 ,num_pages+1)]
        parse_routines = await asyncio.gather(*(AsyncRequest.get(url, delay=Config.REQUEST_DELAY, session=session) \
                                                    for url in page_links), return_exceptions=True)
        if create_session: # close session when done
            await session.close()

        # filter out failed routines
        for page_url, routine in zip(page_links, parse_routines):
            if isinstance(routine, Exception):
                if debug:
                    print(f"Failed to request for page: {page_url}. Error: \n {repr(routine)}")
                continue

            content, request_info = routine
            pages_content.append(content)

        page_links.insert(0, category_url) # first page
        # populate links
        for page_url, content in zip(page_links, pages_content):
            # routine should be of type list
            parsed_movie_urls = _parse_urls_from_page(content, debug=debug) 
            print(f"{page_url} has {len(parsed_movie_urls)} movie links")
            movie_urls += parsed_movie_urls

        return movie_urls

    @classmethod
    async def get_categorized_movie_urls(cls, category_urls, concurrent=True, debug=False):
        categorized_movies = {}
        total = 0
        #concurrently scrape movie urls for all categories
        if concurrent:
            async with AsyncSession() as session:
                parse_routines = await asyncio.gather(*( \
                        cls.get_movie_urls(url, session=session, debug=debug) \
                            for url in category_urls), return_exceptions=True)
    
            for routine, category in zip(parse_routines, category_urls):
                if isinstance(routine, Exception):
                    if debug:
                        print(f"Failed to grab movie links for category {category}. Error: \n {repr(routine)}")
                    continue
                categorized_movies[category] = routine
                total += len(categorized_movies[category])
        else:
            for category in category_urls:
                try:
                    async with AsyncSession() as session:
                        categorized_movies[category] = await cls.get_movie_urls(category, session=session, debug=debug)
                        total += len(categorized_movies[category])
                except Exception as e:
                    if debug:
                        print(f"Failed to grab movie links for category {category}. Error: \n {repr(e)}")
                    continue

        return categorized_movies, total


if __name__ == "__main__":
    import asyncio
    eloop = asyncio.new_event_loop()
    start = time.time()
    categories = eloop.run_until_complete(GeneralParser.get_categories_page(debug=True))
    categorized_movies_urls, total_links = eloop.run_until_complete(GeneralParser.get_categorized_movie_urls(categories, concurrent=True, debug=True))
    print(f"Parsing completed in {time.time() - start} seconds. "
          f"Total of {total_links} links.")



