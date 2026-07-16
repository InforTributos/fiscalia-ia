from __future__ import annotations

from application.use_cases.analizar_grafo_riesgo import AnalizarGrafoRiesgoUseCase
from domain.fiscal.dossier import construir_expediente_fiscal, expediente_to_markdown


class GenerarExpedienteFiscalUseCase:
    def __init__(self, grafo_use_case: AnalizarGrafoRiesgoUseCase | None = None):
        self.grafo_use_case = grafo_use_case or AnalizarGrafoRiesgoUseCase()

    async def generar(self, contribuyente_nit: str, periodo: str, min_pares: int = 10) -> dict:
        grafo = await self.grafo_use_case.analizar_nit(
            contribuyente_nit=contribuyente_nit,
            periodo=periodo,
            min_pares=min_pares,
            incluir_comportamiento=True,
        )
        expediente = construir_expediente_fiscal(grafo)
        expediente["markdown"] = expediente_to_markdown(expediente)
        return expediente

