from bilutv.config import Config
from utils.helper import normalize_url
from custom_request.request import AsyncSession, AsyncRequest
from bs4 import BeautifulSoup
import typing
import time

def _get_num_pages(content, debug=False):
            n_pages = 1
            try:
                html_parser = BeautifulSoup(content, "html.parser")
                page_last = html_parser.find("div", class_="pagination").find("ul").findAll("li")[-1].get_text()
                # https://vuviphimmoi.com/anime/page/1
                n_pages = int(page_last)
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
        for film_box in html_parser.findAll("li", class_="film-item"):
            links.append(film_box.find("a")["href"])

        return links;
    except Exception as e:
        if debug:
            print("_parse_urls_from_page()", repr(e))
    return links


class GeneralParser:

    @classmethod
    async def get_categories_page(cls, debug = False):
        return [
            "https://bilutv.org/the-loai/phim-18.html",
            "https://bilutv.org/the-loai/hanh-dong.html",
            "https://bilutv.org/the-loai/vo-thuat-kiem-hiep.html",
            "https://bilutv.org/the-loai/tam-ly-tinh-cam.html",
            "https://bilutv.org/the-loai/hai-huoc.html",
            "https://bilutv.org/the-loai/hoat-hinh.html",
            "https://bilutv.org/the-loai/vien-tuong.html",
            "https://bilutv.org/the-loai/hinh-su.html",
            "https://bilutv.org/the-loai/kinh-di.html",
            "https://bilutv.org/the-loai/chien-tranh.html",
            "https://bilutv.org/the-loai/phieu-luu.html",
            "https://bilutv.org/the-loai/bi-an.html",
            "https://bilutv.org/the-loai/khoa-hoc.html",
            "https://bilutv.org/the-loai/gia-dinh.html",
            "https://bilutv.org/the-loai/cao-boi.html",
            "https://bilutv.org/the-loai/am-nhac.html",
            "https://bilutv.org/the-loai/the-thao.html",
            "https://bilutv.org/the-loai/truyen-hinh.html",
            "https://bilutv.org/the-loai/tv-show.html",
            "https://bilutv.org/the-loai/lich-su.html",
            "https://bilutv.org/the-loai/tai-lieu.html",
            "https://bilutv.org/the-loai/xuyen-khong.html",
            "https://bilutv.org/the-loai/co-trang.html",
            "https://bilutv.org/the-loai/hoc-duong.html",
            "https://bilutv.org/the-loai/y-khoa-bac-si.html",
            "https://bilutv.org/the-loai/trailer.html"
        ]

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
    print(categories)
    categorized_movies_urls, total_links = eloop.run_until_complete(GeneralParser.get_categorized_movie_urls(categories, debug=True))
    print(f"Parsing completed in {time.time() - start} seconds. "
          f"Total of {total_links} links.")



