from cache.response_cache import MemoryCache

_cache_instance: MemoryCache | None = None


def get_cache() -> MemoryCache:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = MemoryCache()
    return _cache_instance
