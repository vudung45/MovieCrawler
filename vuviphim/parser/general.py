from vuviphim.config import Config
from utils.helper import normalize_url
from custom_request.request import AsyncSession, AsyncRequest
from bs4 import BeautifulSoup
import typing
import time
import re
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
    async def get_movie_urls(cls, category_url, debug=False):
        def get_num_pages(content):
            n_pages = 1
            try:
                html_parser = BeautifulSoup(content, "html.parser")
                page_of_text = html_parser.find("div", class_="pagination").find("span")
                #Page 1 of 30 --> regex for 30
                n_pages = int(re.search(r"Page \d* of (\d*)", str(page_of_text)).group(1))
            except Exception as e:
                if debug:
                    print(f"get_num_pages()\n{repr(e)}")
            return n_pages

        def parse_urls_from_page(content, debug=False):
            """
            get movie urls from a page
            """
            n_pages = 0
            links = []
            try:
                html_parser = BeautifulSoup(content, "html.parser")
                for film_box in html_parser.find("div", class_="items").findAll("article"):
                    links.append(film_box.find("div", class_="poster").find("a")["href"])
                if debug:
                    print(links)
                return links;
            except Exception as e:
                if debug:
                    print(f"parse_urls_from_page() \n{repr(e)}")
            return links

        links = []
        try:
            # use the same session to concurrently call urls from KhoaiTV page
            async with AsyncSession() as session:
                body, request_info = await AsyncRequest.get(category_url, delay=Config.REQUEST_DELAY, session=session)
                num_pages = get_num_pages(body)
                pages_content = [body]
                # all page links except the first page
                page_links = (Config.CATEGORY_PAGINATION_URL.format(\
                                    category_url=normalize_url(category_url), page=page) 
                                        for page in range(2,num_pages+1))
                parse_routines = await asyncio.gather(*(AsyncRequest.get(url, delay=Config.REQUEST_DELAY, session=session) for url in page_links))
                pages_content += [routine[0] for routine in parse_routines if type(routine) != Exception]
                for i, content in enumerate(pages_content):
                    # routine should be of type list
                    links += parse_urls_from_page(content, debug=debug) 
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



