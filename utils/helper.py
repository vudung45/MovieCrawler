import re
from custom_request.request import AsyncSession
import functools
import asyncio
from bson import ObjectId
import json
import re

def normalize_url(url):
    return re.sub(r"/+$","", url)

def chunk_iterator(l, n): 
      
    # looping till length l 
    iterator = iter(l)
    for i in range(0, len(l), n):  
        yield (next(iterator) for j in range(i, min(len(l), i + n)))



def inject_async_session(func):
    '''
        decorator to manually create AsyncSession if not given
    '''
    @functools.wraps(func)
    async def wrapped(*args, session=None, **kwargs):
        need_close = session is None
        if not session:
            session = AsyncSession()
        try:
            result = await func(*args, session=session, **kwargs)
            if need_close:
                await session.close()
            return result
        except Exception as e:
            if need_close:
               await session.close()
            raise e
    return wrapped


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)

INTAB = "ạảãàáâậầấẩẫăắằặẳẵóòọõỏôộổỗồốơờớợởỡéèẻẹẽêếềệểễúùụủũưựữửừứíìịỉĩýỳỷỵỹđẠẢÃÀÁÂẬẦẤẨẪĂẮẰẶẲẴÓÒỌÕỎÔỘỔỖỒỐƠỜỚỢỞỠÉÈẺẸẼÊẾỀỆỂỄÚÙỤỦŨƯỰỮỬỪỨÍÌỊỈĨÝỲỶỴỸĐ"
INTAB = [ch for ch in INTAB]


OUTTAB = "a" * 17 + "o" * 17 + "e" * 11 + "u" * 11 + "i" * 5 + "y" * 5 + "d" + \
         "A" * 17 + "O" * 17 + "E" * 11 + "U" * 11 + "I" * 5 + "Y" * 5 + "D"

r = re.compile("|".join(INTAB))
replaces_dict = dict(zip(INTAB, OUTTAB))


def no_accent_vietnamese(utf8_str):
    return r.sub(lambda m: replaces_dict[m.group(0)], utf8_str)

if __name__ == "__main__":
    print(no_accent_vietnamese("Vãi cả đái"))