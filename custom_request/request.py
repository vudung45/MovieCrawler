import aiohttp
from urllib.parse import urlparse, urlencode, quote
import time
import asyncio
from  aiohttp.client_exceptions import ClientResponseError
from utils.retryable import retryable_async


class AsyncSession(aiohttp.ClientSession):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)   
        self.access = {}

    async def delay_access(self, domain, delay):
        """
            put the task into sleep if still in delay interval
        """
        if domain in self.access:
            while self.access[domain] + delay > time.time():
                await asyncio.sleep(self.access[domain] + delay - time.time())
            
        self.access[domain] = time.time()

    @retryable_async(exceptions=[ClientResponseError])
    async def get(self, url, *args, delay=0.01, use_proxy=False, **kwargs):
        domain = urlparse(url).netloc
        await self.delay_access(domain, delay)
        if use_proxy:
            url = f"https://feedback.googleusercontent.com/gadgets/proxy?container=focus&url={quote(url)}"

        r =  await super().get(url, *args, **kwargs)
        return r

    @retryable_async(exceptions=[ClientResponseError])
    async def post(self, url, *args, **kwargs):
        domain = urlparse(url).netloc
        await self.delay_access(domain, delay)
        r =  await super().post(url, *args,**kwargs)
        return r
        
class AsyncRequest:

    @classmethod
    def new_session(cls, **kwargs):
        return AsyncSession(**kwargs)

    @classmethod
    @retryable_async(exceptions=[ClientResponseError])
    async def get(cls, url, *args, delay=0.01, session=None, **kwargs):
        if not session:
            async with cls.new_session() as session:
                r = await session.get(url, *args, delay=delay, **kwargs)
                r.raise_for_status()
                return await r.text(), r.request_info
        else:
            r = await session.get(url, *args, delay=delay,**kwargs)
            r.raise_for_status()
            return await r.text(), r.request_info

    @classmethod
    async def post(cls, url, *args, **kwargs):
        cls.session.get(url, *args, **kwargs)


