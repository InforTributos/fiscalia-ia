from __future__ import annotations

from application.use_cases.analizar_comportamiento import AnalizarComportamientoUseCase
from domain.errors import NITNoEncontradoError
from domain.graph.network_score import calcular_riesgo_red
from domain.graph.taxpayer_graph import build_taxpayer_graph, graph_to_dict
from infrastructure.mcp.graph import OracleGraphRepository


class AnalizarGrafoRiesgoUseCase:
    def __init__(
        self,
        graph_repo: OracleGraphRepository | None = None,
        comportamiento_use_case: AnalizarComportamientoUseCase | None = None,
    ):
        self.graph_repo = graph_repo or OracleGraphRepository()
        self.comportamiento_use_case = comportamiento_use_case or AnalizarComportamientoUseCase()

    async def analizar_nit(
        self,
        contribuyente_nit: str,
        periodo: str,
        min_pares: int = 10,
        incluir_comportamiento: bool = True,
    ) -> dict:
        contribuyente = await self.graph_repo.obtener_contribuyente(contribuyente_nit)
        if not contribuyente:
            raise NITNoEncontradoError(contribuyente_nit)

        analisis_comportamental = None
        if incluir_comportamiento:
            analisis_comportamental = await self.comportamiento_use_case.analizar_nit(
                contribuyente_nit=contribuyente_nit,
                periodo=periodo,
                min_pares=min_pares,
            )

        relacionados = await self.graph_repo.obtener_relacionados(contribuyente)
        graph = build_taxpayer_graph(contribuyente, relacionados, analisis_comportamental)
        score_comportamental = (analisis_comportamental or {}).get("score_comportamental", 0.0)
        riesgo = calcular_riesgo_red(graph, score_comportamental=score_comportamental)

        return {
            **graph_to_dict(graph),
            "periodo": periodo,
            "resumen_red": riesgo,
            "analisis_comportamental": analisis_comportamental,
        }

