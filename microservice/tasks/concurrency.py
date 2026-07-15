import asyncio
import logging

logger = logging.getLogger(__name__)

_MAX = 2
_lock = asyncio.Lock()
_active: dict[str, asyncio.Event] = {}


async def esperar_turno(proceso_id: str) -> asyncio.Event:
    cancel_event = asyncio.Event()
    while True:
        async with _lock:
            if len(_active) < _MAX and proceso_id not in _active:
                _active[proceso_id] = cancel_event
                return cancel_event
        await asyncio.sleep(2)


def liberar_slot(proceso_id: str) -> None:
    entry = _active.pop(proceso_id, None)
    if entry:
        logger.debug("Slot liberado para proceso %s", proceso_id)


def cancelar(proceso_id: str) -> bool:
    cancel_event = _active.get(proceso_id)
    if cancel_event:
        cancel_event.set()
        logger.info("Proceso %s cancelado via gestor de concurrencia", proceso_id)
        return True
    return False


def esta_activo(proceso_id: str) -> bool:
    cancel_event = _active.get(proceso_id)
    if cancel_event is None:
        return True  # no registrado en el gestor = no cancelado
    return not cancel_event.is_set()


def activos() -> int:
    return len(_active)
