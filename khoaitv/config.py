

class Config:
    BASE_URL = "https://khoaitv.org/"
    CATEGORY_URL = f"{BASE_URL}/the-loai"
    CATEGORY_PAGINATION_URL = "{category_url}/page/{page}"
    REQUEST_DELAY = 0.02 # in seconds