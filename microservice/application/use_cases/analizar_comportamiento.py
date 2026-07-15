from __future__ import annotations

import uuid

from domain.behavioral.behavioral_score import calcular_score_comportamental
from domain.behavioral.peer_group import build_benchmark, build_contributor_metrics
from domain.errors import NITNoEncontradoError, ProcesoNoEncontradoError
from infrastructure.mcp.behavioral import OracleBehavioralRepository
from infrastructure.persistence.repositorio_proceso import PostgresProcesoRepo


class AnalizarComportamientoUseCase:
    def __init__(
        self,
        behavioral_repo: OracleBehavioralRepository | None = None,
        proceso_repo: PostgresProcesoRepo | None = None,
    ):
        self.behavioral_repo = behavioral_repo or OracleBehavioralRepository()
        self.proceso_repo = proceso_repo or PostgresProcesoRepo()

    async def analizar_nit(
        self,
        nit: str,
        periodo: str,
        ciiu: str | None = None,
        regimen: str | None = None,
        min_pares: int = 10,
    ) -> dict:
        row = await self.behavioral_repo.obtener_contribuyente(nit, periodo)
        if not row:
            raise NITNoEncontradoError(nit)

        contribuyente = build_contributor_metrics(row, periodo)
        ciiu_ref = ciiu or contribuyente.ciiu
        regimen_ref = regimen if regimen is not None else contribuyente.regimen

        pares_rows = await self.behavioral_repo.obtener_pares(periodo, ciiu_ref, regimen_ref)
        pares = [
            build_contributor_metrics(peer, periodo)
            for peer in pares_rows
            if str(peer.get("nit", "")) != contribuyente.nit
        ]
        benchmark = build_benchmark(pares, ciiu_ref, regimen_ref or "", periodo)
        return calcular_score_comportamental(contribuyente, pares, benchmark, min_pares=min_pares)

    async def ranking_proceso(
        self,
        proceso_id: uuid.UUID,
        periodo: str | None = None,
        limite: int = 50,
        min_score: float = 0,
        min_pares: int = 10,
    ) -> dict:
        proceso = await self.proceso_repo.obtener_proceso(proceso_id)
        if not proceso:
            raise ProcesoNoEncontradoError(str(proceso_id))

        criteria = proceso.get("criteria") or {}
        periodo_ref = periodo or criteria.get("periodo") or criteria.get("vigencia_fin") or "2024"
        _, detalles = await self.proceso_repo.listar_proceso_detalle(
            proceso_id=proceso_id,
            page=1,
            page_size=min(max(limite * 3, limite), 500),
            ordenar_por="mcp_score",
            direccion="desc",
        )

        resultados = []
        errores = []
        for detalle in detalles:
            nit = detalle.get("nit")
            if not nit:
                continue
            try:
                analisis = await self.analizar_nit(str(nit), str(periodo_ref), min_pares=min_pares)
            except Exception as exc:
                errores.append({"nit": nit, "mensaje": str(exc)})
                continue
            if analisis["score_comportamental"] >= min_score:
                resultados.append(analisis)

        resultados.sort(key=lambda item: item["score_comportamental"], reverse=True)
        return {
            "proceso_id": str(proceso_id),
            "periodo": str(periodo_ref),
            "total_evaluados": len(detalles),
            "total_rankeados": len(resultados[:limite]),
            "errores": errores,
            "resultados": resultados[:limite],
        }

