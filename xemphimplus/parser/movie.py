
from typing import List, Optional, Any, Dict
from custom_request.request import AsyncRequest, AsyncSession
from utils.helper import inject_async_session
from xemphimplus.config import Config
from bs4 import BeautifulSoup
import asyncio
import re

SWITCHER = {
    "Năm xuất bản": "year",
    "Đang phát": "status",
    "Thời lượng": "duration",
    "Thể loại": "genres",
    "Quốc gia": "country",
    "Diễn viên": "casts",
    "Đạo diễn": "directors"
}

class MovieParser:

    @classmethod
    @inject_async_session
    async def get_episodes_urls(self, url: str, content=None, session = None, debug=False) -> List[str]:
        '''
        url: http://khoaitv.org/phim/shameless-season-10-mat-day-phan-10-13270

        URL has to be a watch button url
        '''
        if not content:
            content, _ = await AsyncRequest.get(url, delay=Config.REQUEST_DELAY, session=session)

        html_parse = BeautifulSoup(content, "html.parser")
        try:
            urls = []
            for server in html_parse.find("div", id="halim-list-server").findAll("div", class_="halim-server"):
                for li in server.find("ul").findAll("li"):
                    if li.find("a"):
                        urls.append({server.find("span").text.strip()+"_"+li.find("a").text.strip() : li.find("a")["href"]})
                    elif li.find("span") and li.find("span")["data-href"]:
                        urls.append({server.find("span").text.strip()+"_"+li.find("span").text.strip() : li.find("span")["data-href"]})
            return urls
        except Exception as e:
            if debug:
                print(f"get_episodes_urls(). Error: \n {repr(e)}")
                
        return []

    @classmethod
    @inject_async_session
    async def get_movie_info(self, url: str, content=None, pre_metadata = None, session = None, debug=False) -> Optional[Dict[str, str]]:
        global SWITCHER

        try:
            if not content:
                content, request_info = await AsyncRequest.get(url, delay=Config.REQUEST_DELAY, use_proxy=Config.USE_PROXY, session=session)
            html_parse = BeautifulSoup(content, "html.parser")
            metadata = {
                "title_vietnamese": html_parse.find("h1", class_="entry-title").text.strip()
            }
            if pre_metadata:
                metadata = {**metadata, **pre_metadata}

            metadata["watch_url"] = html_parse.find("a", class_="play-btn")["href"]
            metadata["image"] = html_parse.find("img", class_="movie-thumb")["src"]
            metadata["vietnamese_description"] = html_parse.find("article", class_="item-content").text.strip()
            metadata["genres"] = html_parse.find("div", class_="more-info").findAll("span")[-1].text.strip()
            metadata["duration"] = html_parse.find("div", class_="more-info").findAll("span")[-1].text.strip()
            try:
                metadata["year"] = html_parse.find("span", class_="title-year").text.strip().replace("(", "").replace(")", "")
                metadata["year"] = re.match(r"(\d*)", metadata["year"])[1]
            except Exception as e:
                print(e)

            metadata["movie_id"] = url.split("/")[-1].strip()
            metadata["origin"] = Config.IDENTIFIER
            return metadata
        except Exception as e:
            raise e
            if debug:
                print(f"get_movie_info(). Error: \n {repr(e)}")
        return None


    @classmethod
    @inject_async_session
    async def get_watch_button_url(self, url: str, content=None, asession = None, debug=False) -> Optional[str]:
        if not content:
            content, request_info = await AsyncRequest.get(url, delay=Config.REQUEST_DELAY, use_proxy=Config.USE_PROXY, session=session)

        try:
            html_parse = BeautifulSoup(content, "html.parser")
            return html_parse.find("a", class_="play-film")["href"]
        except Exception as e:
            if debug:
                print(f"get_watch_button_url(). Error: \n {repr(e)}")

        return None

if __name__ == "__main__":
    eloop = asyncio.new_event_loop()
    #metadata = eloop.run_until_complete(MovieParser.get_movie_info("https://bilutv.org/phim-son-hai-kinh-chi-thuong-co-mat-uoc-i1-16271.html", debug=True))
    #print(metadata)
    episodes_urls = eloop.run_until_complete(MovieParser.get_episodes_urls("http://xemphimplus.net/xem-phim-diep-van-4-hoi-ket/tap-cam-sv1.html", debug=True))
    print(episodes_urls)



        