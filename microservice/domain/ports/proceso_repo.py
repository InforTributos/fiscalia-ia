from abc import ABC, abstractmethod
from uuid import UUID


class ProcesoRepo(ABC):
    @abstractmethod
    async def crear_cliente(self, nit: str, razon_social: str) -> UUID | None:
        ...

    @abstractmethod
    async def obtener_cliente_por_nit(self, nit: str) -> dict | None:
        ...

    @abstractmethod
    async def crear_proceso(self, cliente_id: UUID, nombre: str, criteria: dict) -> UUID | None:
        ...

    @abstractmethod
    async def obtener_proceso_por_criteria(self, cliente_id: UUID, criteria: dict) -> dict | None:
        ...

    @abstractmethod
    async def obtener_proceso(self, id: UUID) -> dict | None:
        ...

    @abstractmethod
    async def crear_intento(self, proceso_id: UUID, numero: int = 1) -> int | None:
        ...

    @abstractmethod
    async def actualizar_estado_proceso(self, id: UUID, estado: str, **kwargs):
        ...

    @abstractmethod
    async def actualizar_estado_intento(self, id: int, estado: str, error_resumen: str | None = None):
        ...

    @abstractmethod
    async def obtener_ultimo_intento(self, proceso_id: UUID) -> dict | None:
        ...

    @abstractmethod
    async def obtener_historial_intentos(self, proceso_id: UUID) -> list[dict]:
        ...

    @abstractmethod
    async def actualizar_progreso_intento(self, id: int, procesados: int, errores_count: int):
        ...

    @abstractmethod
    async def obtener_cliente_por_id(self, cliente_id: UUID) -> dict | None:
        ...

    @abstractmethod
    async def insertar_detalle(self, proceso_id: UUID, intento_id: int, **kwargs) -> int | None:
        ...

    @abstractmethod
    async def actualizar_resultado_detalle(self, id: int, **kwargs):
        ...

    @abstractmethod
    async def insertar_error_proceso(self, proceso_id: UUID, intento_id: int, capa: str, codigo: str, mensaje: str, contexto: dict | None = None):
        ...

    @abstractmethod
    async def insertar_error_detalle(self, detalle_id: int, nit: str, capa: str, codigo: str, mensaje: str, contexto: dict | None = None):
        ...

    @abstractmethod
    async def listar_proceso_detalle(self, proceso_id: UUID, **filtros):
        ...

    @abstractmethod
    async def listar_errores(self, proceso_id: UUID, **filtros):
        ...
