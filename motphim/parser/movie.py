
from typing import List, Optional, Any, Dict
from custom_request.request import AsyncRequest, AsyncSession
from utils.helper import inject_async_session
from motphim.config import Config
from bs4 import BeautifulSoup
import asyncio
import urllib.parse
import re

SWITCHER = {
    "Năm sản xuất": "year",
    "Trạng thái": "status",
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
        url: https://motphim.net/xem-phim/luong-the-hoan-tap-1-6494_81580.html

        URL has to be a watch button url
        '''
        if not content:
            content, _ = await AsyncRequest.get(url, delay=Config.REQUEST_DELAY, session=session)

        html_parse = BeautifulSoup(content, "html.parser")
        try:
            # Tap 1 Preview -> 1 Preview  (Split "Tap ")
            return [{" ".join(a.text.strip().split(" ")[1:]) : urllib.parse.urljoin(Config.BASE_URL, a["href"])} 
                                                for a in html_parse.find("div", class_="list-episode").findAll("a")]
        except Exception as e:
            if debug:
                print(f"get_episodes_urls(). Error: \n {repr(e)}")

        return []

    @classmethod
    @inject_async_session
    async def get_movie_info(self, url: str, content=None, session = None, debug=False) -> Optional[Dict[str, str]]:
        global SWITCHER

        try:
            if not content:
                content, request_info = await AsyncRequest.get(url, delay=Config.REQUEST_DELAY, session=session)
            html_parse = BeautifulSoup(content, "html.parser")
            metadata = {
                "title": html_parse.find("span", class_="real-name").text.strip(),
                "title_vietnamese": html_parse.find("span", class_="title").text.strip()
            }

            metadata["watch_url"] = await self.get_watch_button_url(url, content, session=session, debug=True)
            metadata["image"] = html_parse.find("div", class_="poster").find("img")["src"]
            metadata["vietnamese_description"] = html_parse.find("div", class_="tabs-content").find("div", class_="tab").text.strip(),
            fields = [dt.text.strip()[:-1] for dt in html_parse.find("div", class_="dinfo").find("dl", class_="col").findAll("dt")]
            contents = [dd.text.strip() for dd in html_parse.find("div", class_="dinfo").find("dl", class_="col").findAll("dd")]
            
            for field, content in zip(fields, contents):
                if field in SWITCHER:
                    metadata[SWITCHER[field]] = content.strip() # clean leading white spaces

            metadata["movie_id"] = re.match(r".*-(\d*).html$", url)[1].strip()
            metadata["origin"] = Config.IDENTIFIER
            return metadata
        except Exception as e:
            raise e
            if debug:
                print(f"get_movie_info(). Error: \n {repr(e)}")
        return None


    @classmethod
    @inject_async_session
    async def get_watch_button_url(self, url: str, content=None, session = None, debug=False) -> Optional[str]:
        if not content:
            content, request_info = await AsyncRequest.get(url, delay=Config.REQUEST_DELAY, session=session)

        try:
            html_parse = BeautifulSoup(content, "html.parser")
            for btn in html_parse.findAll("a", class_="btn-see"):
                if "Xem phim" in btn.text.strip():
                    return urllib.parse.urljoin(Config.BASE_URL, btn["href"])

            return None
        except Exception as e:
            if debug:
                print(f"get_watch_button_url(). Error: \n {repr(e)}")

        return None

if __name__ == "__main__":
    eloop = asyncio.new_event_loop()
    metadata = eloop.run_until_complete(MovieParser.get_movie_info("https://motphim.net/phim/chien-tranh-giua-cac-vi-sao-7-than-luc-thuc-tinh-548.html", debug=True))
    print(metadata)
    episodes_urls = eloop.run_until_complete(MovieParser.get_episodes_urls(metadata["watch_url"], debug=True))
    print(episodes_urls)



        