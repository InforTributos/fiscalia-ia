from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    content: str
    tokens_entrada: int = 0
    tokens_salida: int = 0
    provider: str = ""
    modelo: str = ""


class LLMProvider(ABC):
    name: str = ""

    @abstractmethod
    async def chat_json(self, messages: list[dict], schema: dict | None = None) -> dict:
        ...

    async def discover_models(self) -> list[str]:
        """Consulta la API del proveedor para listar modelos disponibles.
        Retorna lista vacía si el proveedor no soporta descubrimiento."""
        return []
