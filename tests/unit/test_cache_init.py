from cache import get_cache
from cache.response_cache import MemoryCache


def test_get_cache_returns_singleton():
    c1 = get_cache()
    c2 = get_cache()
    assert c1 is c2
    assert isinstance(c1, MemoryCache)
