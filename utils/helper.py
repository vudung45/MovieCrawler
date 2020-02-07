import re

def normalize_url(url):
    return re.sub(r"/+$","", url)