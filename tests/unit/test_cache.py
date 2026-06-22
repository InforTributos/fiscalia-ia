import time

from cache.response_cache import MemoryCache


def test_cache_guardar_y_obtener():
    cache = MemoryCache()
    cache.guardar("test-key", {"data": 123})
    resultado = cache.obtener("test-key")
    assert resultado == {"data": 123}


def test_cache_miss_retorna_none():
    cache = MemoryCache()
    resultado = cache.obtener("key-no-existe")
    assert resultado is None


def test_cache_expira_por_ttl():
    cache = MemoryCache()
    cache.ttl = 0
    cache.guardar("test-key", {"data": 123})
    time.sleep(0.1)
    resultado = cache.obtener("test-key")
    assert resultado is None


def test_cache_size():
    cache = MemoryCache()
    assert cache.size == 0
    cache.guardar("key1", "val1")
    cache.guardar("key2", "val2")
    assert cache.size == 2


def test_cache_limpiar():
    cache = MemoryCache()
    cache.guardar("key1", "val1")
    cache.limpiar()
    assert cache.size == 0
