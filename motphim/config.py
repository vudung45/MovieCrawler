

class FakeFString:
    def __init__(self, format_logic):
        self.format_logic = format_logic

    def format(self, *args, **kwargs):
        return self.format_logic(*args, **kwargs)


def format_logic(category_url=None, page=None):
    category_url = category_url.split(".html")[0]
    return f"{category_url}-{page}.html"

class Config:
    BASE_URL = "https://motphim.net/"
    CATEGORY_URL = f"{BASE_URL}/the-loai"
    CATEGORY_PAGINATION_URL = FakeFString(format_logic)
    REQUEST_DELAY = 0.2 # in seconds
    IDENTIFIER = "motphim"
    USE_PROXY = True