import functools
import asyncio 

def retryable_async(exceptions=[], delay=0.1, multipler=2, retries=5):
    settings = {
        "exceptions" : exceptions,
        "delay": delay,
        "multipler": multipler,
        "retries": retries
    }

    def wrapper(func):
        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            exceptions, delay, multipler, retries = settings["exceptions"], settings["delay"], settings["multipler"], settings["retries"]
            if "retry" in kwargs and not kwargs["retry"]:
                retries = 0
                
            while retries > 0:
                retries -= 1
                try:
                    return await func(*args,  **kwargs)
                except Exception as e:
                    excluded = any(isinstance(e, excep) for excep in exceptions)
                    if excluded:
                        print(f"Retying... {func.__name__}({args}, {kwargs}). Exception: {repr(e)}")
                        await asyncio.sleep(delay*multipler)
                        multipler *= multipler
                        continue
                    raise e
            return await func(*args,  **kwargs)
        return wrapped
    return wrapper