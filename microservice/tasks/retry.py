import asyncio
import logging

from config import settings

logger = logging.getLogger(__name__)


async def with_retry(
    func, *args,
    max_attempts: int | None = None,
    retry_on: tuple[type[Exception], ...] | None = None,
    **kwargs,
):
    attempts = max_attempts or settings.retry_max_attempts
    retry_on = retry_on or (Exception,)
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            return await func(*args, **kwargs)
        except retry_on as e:
            last_error = e
            if attempt < attempts:
                wait = settings.retry_backoff_factor ** attempt
                logger.warning("Intento %d/%d falló: %s. Reintentando en %ds", attempt, attempts, str(e), wait)
                await asyncio.sleep(wait)
        except Exception:
            raise

    raise last_error
