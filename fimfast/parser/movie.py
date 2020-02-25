
from typing import List, Optional, Any, Dict
from custom_request.request import AsyncRequest, AsyncSession
from utils.helper import inject_async_session
from fimfast.config import Config
from bs4 import BeautifulSoup
import asyncio
import re
import uuid
import json
import urllib.parse


SWITCHER = {
    "Năm sản xuất": "year",
    "Cập nhật": "status",
    "Thời lượng": "duration",
    "Thể loại": "genres",
    "Quốc gia": "country"
}

FAKE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.116 Safari/537.36",
    "Origin": "https://fimfast.com"
}

GET_EPISODES_API = "https://fimfast.com/api/v2/films/{episode_id}/episodes?sort=name"

class MovieParser:

    @classmethod
    @inject_async_session
    async def get_episodes_urls(self, url: str, content=None, aux = None, session = None, debug=False) -> List[str]:
        '''
        url: http://khoaitv.org/phim/shameless-season-10-mat-day-phan-10-13270

        URL has to be a watch button url
        '''
        if not content:
            content, _ = await AsyncRequest.get(url, headers = FAKE_HEADERS, delay=Config.REQUEST_DELAY, session=session)

        html_parse = BeautifulSoup(content, "html.parser")
        try:
            if html_parse.find("div", class_="tab-episode"):
                episode_id = html_parse.find("div", class_="container")["data-id"].strip()
                resp, _ = await AsyncRequest.get(GET_EPISODES_API.format(episode_id=episode_id), headers = {**FAKE_HEADERS,
                                                        "Referer": url, 
                                                        "X-Requested-With": "XMLHttpRequest",
                                                        "Cookie": f"__cfduid={str(uuid.uuid1()).replace('-','')}"}, 
                                            delay=Config.REQUEST_DELAY, session=session)
                jsonResp = json.loads(resp)

                urls = [ { str(item["name"]) : urllib.parse.urljoin(Config.BASE_URL, item["link"])} for item in jsonResp["data"]]
                return urls
            else: # not an episodic movie
                return [{ "FULL": url}]
        except Exception as e:
            if debug:
                print(f"get_episodes_urls(). Error: \n {repr(e)}")
                
        return []

    @classmethod
    @inject_async_session
    async def get_movie_info(self, url: str, content=None, aux=None, pre_metadata = None, session = None, debug=False) -> Optional[Dict[str, str]]:
        global SWITCHER
        try:
            if not content:
                content, request_info = await AsyncRequest.get(url, headers= FAKE_HEADERS, delay=Config.REQUEST_DELAY, session=session)
            html_parse = BeautifulSoup(content, "html.parser")

            metadata = pre_metadata if pre_metadata else {}

            metadata["title_vietnamese"] = html_parse.find("h1", class_="film-info-title").text.strip()
            metadata["watch_url"] = url;
            metadata["vietnamese_description"] = html_parse.find("div", class_="film-info-description").text.strip()

            for div in html_parse.findAll("div", class_="film-info-genre"):
                try:
                    field, val = div.text.split(":")[0], ":".join(div.text.split(":")[1:])
                    field = field.strip()
                    val = val.strip()
                    if field == "Tên tiếng Anh":
                        # Itaewon Keullasseu / Itaewon Class
                        tmp = val.split("/")
                        metadata["title"] = tmp[0].strip() if len(tmp) == 1 else tmp[1].strip()

                    if field in SWITCHER:
                        metadata[SWITCHER[field]] = val
                except Exception as e:
                    print("Error parsing field: "+div.text)
                    print(e)
            metadata["year"] = re.match(r"(\d*)", metadata["year"])[1]
            metadata["genres"] = metadata["genres"].replace("\xa0\n"," ") if "genres" in metadata else ""
            metadata["movie_id"] = html_parse.find("div", class_="container")["data-id"].strip()
            metadata["origin"] = Config.IDENTIFIER
            return metadata
        except Exception as e:
            if debug:
                print(f"get_movie_info(). Error: \n {repr(e)}")
        return None


    @classmethod
    @inject_async_session
    async def get_watch_button_url(self, url: str, content=None, aux=None, session = None, debug=False) -> Optional[str]:
        return url

if __name__ == "__main__":
    eloop = asyncio.new_event_loop()
    metadata = eloop.run_until_complete(MovieParser.get_movie_info("https://fimfast.com/biet-doi-sieu-anh-hung-4-endgame", debug=True))
    print(metadata)
    episodes_urls = eloop.run_until_complete(MovieParser.get_episodes_urls("https://fimfast.com/biet-doi-sieu-anh-hung-4-endgame", debug=True))
    print(episodes_urls)



        