from abc import ABC, abstractmethod


class LLMPort(ABC):
    @abstractmethod
    async def analizar(self, contexto: dict) -> dict:
        ...
