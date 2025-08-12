from functools import lru_cache, wraps
from openad_service_utils.api.config import get_config_instance


def conditional_lru_cache(maxsize=100):
    def decorator(func):
        if get_config_instance().ENABLE_CACHE_RESULTS:
            cached_func = lru_cache(maxsize=maxsize)(func)
            return cached_func
        else:

            @wraps(func)
            def no_cache(*args, **kwargs):
                return func(*args, **kwargs)

            return no_cache

    return decorator
