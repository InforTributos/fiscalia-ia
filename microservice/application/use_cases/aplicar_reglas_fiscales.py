from __future__ import annotations

from application.use_cases.gestionar_hallazgos import GestionarHallazgosUseCase
from domain.fiscalizacion.rule_engine import evaluar_reglas


class AplicarReglasFiscalesUseCase:
    async def evaluar(self, perfil: dict, reglas: list[str] | None = None) -> list[dict]:
        return evaluar_reglas(perfil, reglas=reglas)

    async def ejecutar(self, perfil: dict, reglas: list[str] | None = None) -> list[dict]:
        candidatos = evaluar_reglas(perfil, reglas=reglas)
        gestor = GestionarHallazgosUseCase()
        hallazgos = []
        for candidato in candidatos:
            hallazgos.append(await gestor.crear_hallazgo(candidato))
        return hallazgos

