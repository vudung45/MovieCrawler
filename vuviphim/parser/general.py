from vuviphim.config import Config
from utils.helper import normalize_url, inject_async_session
from custom_request.request import AsyncSession, AsyncRequest
from bs4 import BeautifulSoup
from typing import List, Iterable, Tuple, Dict
import time
import re

def _get_num_pages(content: str, debug=False) -> int:
            n_pages = 1
            try:
                html_parser = BeautifulSoup(content, "html.parser")
                page_of_text = html_parser.find("div", class_="pagination").find("span")
                #Page 1 of 30 --> regex for 30
                n_pages = int(re.search(r"Page \d* of (\d*)", str(page_of_text)).group(1))
            except Exception as e:
                if debug:
                    print(f"_get_num_pages()\n{repr(e)}")
            return n_pages

def _parse_urls_from_page(content: str, debug=False) -> List[str]:
    """
    get movie urls from a page
    """
    n_pages = 0
    links = []
    try:
        html_parser = BeautifulSoup(content, "html.parser")
        for film_box in html_parser.find("div", class_="items").findAll("article"):
            links.append(film_box.find("div", class_="poster").find("a")["href"])
        return links;
    except Exception as e:
        if debug:
            print(f"_parse_urls_from_page() \n{repr(e)}")
    return links

class GeneralParser:

    @classmethod
    async def get_categories_page(cls, debug=False):
        # links = []
        # try:
        #     async with AsyncSession() as session:
        #         res = await session.get(Config.BASE_URL)
        #         res.raise_for_status()
        #         html_parser = BeautifulSoup(await res.text(), "html.parser")
        #         categories = html_parser.find("li", {"id": "menu-item-134"}).find("ul")
        #         for category in categories.findAll("li"):
        #             links.append(category.find("a")["href"])
        # except Exception as e:
        #     if debug:
        #         print(f"get_categories_page() {repr(e)}")
        # return links
        return [
                f"{Config.BASE_URL}/anime/",
                f"{Config.BASE_URL}/phim-hanh-dong",
                f"{Config.BASE_URL}/phim-vo-thuat",
                f"{Config.BASE_URL}/kinh-di",
                f"{Config.BASE_URL}/hai-huoc",
                f"{Config.BASE_URL}/phim-co-trang",
                f"{Config.BASE_URL}/hoat-hinh",
                f"{Config.BASE_URL}/vien-tuong",
                f"{Config.BASE_URL}/giat-gan/",
                f"{Config.BASE_URL}/tam-ly",
                f"{Config.BASE_URL}/tv-show/",
                f"{Config.BASE_URL}/phieu-luu",
                f"{Config.BASE_URL}/than-thoai",
                f"{Config.BASE_URL}/chien-tranh",
                f"{Config.BASE_URL}/toi-pham/",
                f"{Config.BASE_URL}/lich-su",
            ]

    @classmethod
    @inject_async_session
    async def get_movie_urls(cls, category_url: str, session=None, debug=False) -> List[str]:
        
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
    @inject_async_session
    async def get_categorized_movie_urls(cls, category_urls: Iterable[str], concurrent=True, session = None, debug=False) -> Tuple[Dict[str, List[str]], int]:
        categorized_movies = {}
        total = 0
        #concurrently scrape movie urls for all categories
        if concurrent:
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
    categorized_movies_urls, total_links = eloop.run_until_complete(GeneralParser.get_categorized_movie_urls(categories, debug=True))
    print(f"Parsing completed in {time.time() - start} seconds. "
          f"Total of {total_links} links.")



