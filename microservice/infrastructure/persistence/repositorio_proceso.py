from uuid import UUID

from domain.ports.proceso_repo import ProcesoRepo
from infrastructure.persistence import queries


class PostgresProcesoRepo(ProcesoRepo):
    async def crear_cliente(self, nit: str, razon_social: str) -> UUID | None:
        return await queries.crear_cliente(nit, razon_social)

    async def obtener_cliente_por_nit(self, nit: str) -> dict | None:
        return await queries.obtener_cliente_por_nit(nit)

    async def crear_proceso(self, cliente_id: UUID, nombre: str, criteria: dict) -> UUID | None:
        return await queries.crear_proceso(cliente_id, nombre, criteria)

    async def obtener_proceso_por_criteria(self, cliente_id: UUID, criteria: dict) -> dict | None:
        return await queries.obtener_proceso_por_criteria(cliente_id, criteria)

    async def obtener_proceso(self, id: UUID) -> dict | None:
        return await queries.obtener_proceso(id)

    async def crear_intento(self, proceso_id: UUID, numero: int = 1) -> int | None:
        return await queries.crear_intento(proceso_id, numero)

    async def actualizar_estado_proceso(self, id: UUID, estado: str, **kwargs):
        return await queries.actualizar_estado_proceso(id, estado, **kwargs)

    async def actualizar_estado_intento(self, id: int, estado: str, error_resumen: str | None = None):
        return await queries.actualizar_estado_intento(id, estado, error_resumen)

    async def obtener_ultimo_intento(self, proceso_id: UUID) -> dict | None:
        return await queries.obtener_ultimo_intento(proceso_id)

    async def obtener_historial_intentos(self, proceso_id: UUID) -> list[dict]:
        return await queries.obtener_historial_intentos(proceso_id)

    async def actualizar_progreso_intento(self, id: int, procesados: int, errores_count: int):
        return await queries.actualizar_progreso_intento(id, procesados, errores_count)

    async def obtener_cliente_por_id(self, cliente_id: UUID) -> dict | None:
        return await queries.obtener_cliente_por_id(cliente_id)

    async def insertar_detalle(self, proceso_id: UUID, intento_id: int, **kwargs) -> int | None:
        return await queries.insertar_detalle(proceso_id, intento_id, **kwargs)

    async def actualizar_resultado_detalle(self, id: int, **kwargs):
        return await queries.actualizar_resultado_detalle(id, **kwargs)

    async def insertar_error_proceso(self, proceso_id: UUID, intento_id: int, capa: str, codigo: str, mensaje: str, contexto: dict | None = None):
        return await queries.insertar_error_proceso(proceso_id, intento_id, capa, codigo, mensaje, contexto)

    async def insertar_error_detalle(self, detalle_id: int, nit: str, capa: str, codigo: str, mensaje: str, contexto: dict | None = None):
        return await queries.insertar_error_detalle(detalle_id, nit, capa, codigo, mensaje, contexto)

    async def listar_proceso_detalle(self, proceso_id: UUID, **filtros):
        return await queries.listar_proceso_detalle(proceso_id, **filtros)

    async def listar_errores(self, proceso_id: UUID, **filtros):
        return await queries.listar_errores(proceso_id, **filtros)
