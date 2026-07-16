from uuid import UUID

from domain.ports.proceso_repo import ProcesoRepo
from infrastructure.persistence import queries


class PostgresProcesoRepo(ProcesoRepo):
    async def crear_entidad(self, entidad_nit: str, razon_social: str, email: str | None = None) -> UUID | None:
        return await queries.crear_entidad(entidad_nit, razon_social, email)

    async def obtener_entidad_por_nit(self, entidad_nit: str) -> dict | None:
        return await queries.obtener_entidad_por_nit(entidad_nit)

    async def crear_proceso(self, entidad_id: UUID, nombre: str, criteria: dict) -> UUID | None:
        return await queries.crear_proceso(entidad_id, nombre, criteria)

    async def obtener_proceso_por_criteria(self, entidad_id: UUID, criteria: dict) -> dict | None:
        return await queries.obtener_proceso_por_criteria(entidad_id, criteria)

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

    async def obtener_entidad_por_id(self, entidad_id: UUID) -> dict | None:
        return await queries.obtener_entidad_por_id(entidad_id)

    async def insertar_detalle(self, proceso_id: UUID, intento_id: int, **kwargs) -> int | None:
        return await queries.insertar_detalle(proceso_id, intento_id, **kwargs)

    async def bulk_insertar_detalle(self, rows: list[dict]) -> list[int]:
        return await queries.bulk_insertar_detalle(rows)

    async def actualizar_resultado_detalle(self, id: int, **kwargs):
        return await queries.actualizar_resultado_detalle(id, **kwargs)

    async def actualizar_estado_detalle(self, id: int, mensaje: str | None = None, clasificacion: str | None = None):
        return await queries.actualizar_estado_detalle(id, mensaje, clasificacion)

    async def insertar_error_proceso(self, proceso_id: UUID, intento_id: int, capa: str, codigo: str, mensaje: str, contexto: dict | None = None):
        return await queries.insertar_error_proceso(proceso_id, intento_id, capa, codigo, mensaje, contexto)

    async def insertar_error_detalle(self, proceso_id: UUID, detalle_id: int, contribuyente_nit: str, capa: str, codigo: str, mensaje: str, contexto: dict | None = None):
        return await queries.insertar_error_detalle(proceso_id, detalle_id, contribuyente_nit, capa, codigo, mensaje, contexto)

    async def desactivar_entidad(self, entidad_id: UUID) -> None:
        return await queries.desactivar_entidad(entidad_id)

    async def reactivar_entidad(self, entidad_id: UUID) -> None:
        return await queries.reactivar_entidad(entidad_id)

    async def listar_proceso_detalle(self, proceso_id: UUID, **filtros):
        return await queries.listar_proceso_detalle(proceso_id, **filtros)

    async def listar_errores(self, proceso_id: UUID, **filtros):
        return await queries.listar_errores(proceso_id, **filtros)
