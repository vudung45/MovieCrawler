from fimfast.config import Config
from utils.helper import normalize_url, inject_async_session
from custom_request.request import AsyncSession, AsyncRequest
from bs4 import BeautifulSoup
from typing import List, Iterable, Tuple, Dict
import time
import asyncio
import re
import ast
import urllib.parse

def _get_num_pages(content: str, debug=False) -> int:
            n_pages = 1
            try:
                html_parser = BeautifulSoup(content, "html.parser")
                page_last = html_parser.find("ul", class_="pagination").findAll("li")[-2].get_text()
                n_pages = int(page_last)
            except Exception as e:
                if debug:
                    print(f"_get_num_pages()\n{repr(e)}")
            return n_pages

def _parse_urls_from_page(content: str, aux = None, debug=False) -> List[str]:
    """
    get movie urls from a page
    """
    n_pages = 0
    links = []
    try:
        html_parser = BeautifulSoup(content, "html.parser")
        for film_box in html_parser.findAll("div", class_="tray-item"):
            link = urllib.parse.urljoin(Config.BASE_URL, film_box.find("a")["href"])
            links.append(link)
            try:
                if aux != None:
                    previous = aux[link] if link in aux else {}
                    aux[link] = {
                        **previous,
                        "image": film_box.find("img")["data-src"]
                    }
            except Exception as e:
                print(e)
        return links;
    except Exception as e:
        if debug:
            print("_parse_urls_from_page()", repr(e))
    return links

FAKE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.116 Safari/537.36"
}

class GeneralParser:

    @classmethod
    async def get_categories_page(cls, debug = False) -> List[str]:
        return [
            "https://fimfast.com/the-loai/hanh-dong",
            "https://fimfast.com/the-loai/phieu-luu",
            "https://fimfast.com/the-loai/kinh-di",
            "https://fimfast.com/the-loai/tinh-cam",
            "https://fimfast.com/the-loai/hoat-hinh",
            "https://fimfast.com/the-loai/vo-thuat",
            "https://fimfast.com/the-loai/hai-huoc",
            "https://fimfast.com/the-loai/tam-ly",
            "https://fimfast.com/the-loai/vien-tuong",
            "https://fimfast.com/the-loai/than-thoai",
            "https://fimfast.com/the-loai/chien-tranh",
            "https://fimfast.com/the-loai/co-trang",
            "https://fimfast.com/the-loai/am-nhac",
            "https://fimfast.com/the-loai/hinh-su",
            "https://fimfast.com/the-loai/tv-show",
            "https://fimfast.com/the-loai/khoa-hoc",
            "https://fimfast.com/the-loai/tai-lieu",
            "https://fimfast.com/the-loai/other",
            "https://fimfast.com/the-loai/lich-su",
            "https://fimfast.com/the-loai/gia-dinh",
            "https://fimfast.com/the-loai/the-thao",
            "https://fimfast.com/the-loai/kiem-hiep",
            "https://fimfast.com/the-loai/kich-tinh",
            "https://fimfast.com/the-loai/bi-an",
            "https://fimfast.com/the-loai/tieu-su"
        ]

    @classmethod
    @inject_async_session
    async def get_movie_urls(cls, category_url: str, aux = None, session=None, debug=False) -> List[str]:
        
        movie_urls = []
        body, request_info = await AsyncRequest.get(category_url, headers = FAKE_HEADERS, delay=Config.REQUEST_DELAY, use_proxy=Config.USE_PROXY, session=session)
        num_pages = _get_num_pages(body)
        pages_content = [body] # first page is already parsed

        # all page links except the first page
        page_links = [Config.CATEGORY_PAGINATION_URL.format(\
                            category_url=normalize_url(category_url), page=page) 
                                for page in range(2 ,num_pages+1)]
        parse_routines = await asyncio.gather(*(AsyncRequest.get(url, delay=Config.REQUEST_DELAY, headers= FAKE_HEADERS, use_proxy=Config.USE_PROXY, session=session) for url in page_links), return_exceptions=True)

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
            parsed_movie_urls = _parse_urls_from_page(content, aux = aux, debug=debug) 
            print(f"{page_url} has {len(parsed_movie_urls)} movie links")
            movie_urls += parsed_movie_urls

        return movie_urls

    @classmethod
    @inject_async_session
    async def get_categorized_movie_urls(cls, category_urls: Iterable[str], aux = None, concurrent=True, session = None, debug=False) -> Tuple[Dict[str, List[str]], int]:
        categorized_movies = {}
        total = 0
        #concurrently scrape movie urls for all categories
        if concurrent:
            parse_routines = await asyncio.gather(*( \
                    cls.get_movie_urls(url, aux = aux, session=session, debug=debug) \
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
                    categorized_movies[category] = await cls.get_movie_urls(category,  aux = aux, session=session, debug=debug)
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



