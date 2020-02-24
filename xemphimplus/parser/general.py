from xemphimplus.config import Config
from utils.helper import normalize_url, inject_async_session
from custom_request.request import AsyncSession, AsyncRequest
from bs4 import BeautifulSoup
from typing import List, Iterable, Tuple, Dict
import time
import asyncio

def _get_num_pages(content: str, debug=False) -> int:
            n_pages = 1
            try:
                html_parser = BeautifulSoup(content, "html.parser")
                page_last = html_parser.find("ul", class_="page-numbers").findAll("li")[-2].get_text()
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
        for film_box in html_parser.findAll("div", class_="halim-item"):
            link = film_box.find("a", class_="halim-thumb")["href"]
            links.append(link)
            # have to pass as an aux cause this stupid fucking site doesn't include this metadata in their
            # movie page
            if aux != None:
                previous = aux[link] if link in aux else {}
                aux[link] = {
                    **previous,
                    "title": film_box.find("a", class_="halim-thumb").find("p", class_="original_title").text.strip()
                }

        return links;
    except Exception as e:
        if debug:
            print("_parse_urls_from_page()", repr(e))
    return links


class GeneralParser:

    @classmethod
    async def get_categories_page(cls, debug = False) -> List[str]:
        return [
            "http://xemphimplus.net/am-nhac",
            "http://xemphimplus.net/bi-an",
            "http://xemphimplus.net/chien-tranh",
            "http://xemphimplus.net/co-trang",
            "http://xemphimplus.net/gia-dinh",
            "http://xemphimplus.net/hai-huoc",
            "http://xemphimplus.net/hanh-dong",
            "http://xemphimplus.net/hinh-su",
            "http://xemphimplus.net/hoat-hinh",
            "http://xemphimplus.net/khoa-hoc",
            "http://xemphimplus.net/kich-tinh",
            "http://xemphimplus.net/kiem-hiep",
            "http://xemphimplus.net/kinh-di",
            "http://xemphimplus.net/lich-su",
            "http://xemphimplus.net/phieu-luu",
            "http://xemphimplus.net/tai-lieu",
            "http://xemphimplus.net/tam-ly",
            "http://xemphimplus.net/than-thoai",
            "http://xemphimplus.net/the-thao",
            "http://xemphimplus.net/tieu-su",
            "http://xemphimplus.net/tinh-cam",
            "http://xemphimplus.net/vien-tuong",
            "http://xemphimplus.net/vo-thuat",
            "http://xemphimplus.net/tv-show"
        ]

    @classmethod
    @inject_async_session
    async def get_movie_urls(cls, category_url: str, aux = None, session=None, debug=False) -> List[str]:
        
        movie_urls = []
        body, request_info = await AsyncRequest.get(category_url, delay=Config.REQUEST_DELAY, use_proxy=Config.USE_PROXY, session=session)
        num_pages = _get_num_pages(body)
        pages_content = [body] # first page is already parsed

        # all page links except the first page
        page_links = [Config.CATEGORY_PAGINATION_URL.format(\
                            category_url=normalize_url(category_url), page=page) 
                                for page in range(2 ,num_pages+1)]
        parse_routines = await asyncio.gather(*(AsyncRequest.get(url, delay=Config.REQUEST_DELAY, use_proxy=Config.USE_PROXY, session=session) \
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



