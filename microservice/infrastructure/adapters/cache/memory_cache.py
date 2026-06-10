import logging
import time

from config import settings

logger = logging.getLogger(__name__)


class MemoryCache:
    def __init__(self):
        self._cache: dict[str, tuple[float, object]] = {}
        self.ttl = settings.cache_ttl_seconds

    def obtener(self, key: str) -> object | None:
        if key in self._cache:
            ts, valor = self._cache[key]
            if time.time() - ts < self.ttl:
                logger.debug("Cache hit: %s", key)
                return valor
            del self._cache[key]
        return None

    def guardar(self, key: str, valor: object):
        self._cache[key] = (time.time(), valor)

    def limpiar(self):
        self._cache.clear()

    @property
    def size(self) -> int:
        return len(self._cache)
