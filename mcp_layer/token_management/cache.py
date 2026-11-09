import time


CACHE_TTL = 300  # 5 minutes

cache = {}


def set_cache(key: str, value):

    cache[key] = {
        "value": value,
        "created_at": time.time()
    }


def get_cache(key: str):

    if key not in cache:
        return None

    cached_data = cache[key]

    if time.time() - cached_data["created_at"] > CACHE_TTL:
        del cache[key]
        return None

    return cached_data["value"]


def clear_cache(key: str):

    if key in cache:
        del cache[key]