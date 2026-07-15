from __future__ import annotations

import uuid

from application.use_cases.analizar_comportamiento import AnalizarComportamientoUseCase
from application.use_cases.analizar_grafo_riesgo import AnalizarGrafoRiesgoUseCase
from application.use_cases.generar_expediente_fiscal import GenerarExpedienteFiscalUseCase
from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse
from presentation.graph_viewer import render_graph_viewer
from schemas.behavioral import (
    ComportamientoResponse,
    ExpedienteFiscalResponse,
    GrafoRiesgoResponse,
    RankingComportamentalResponse,
)

router = APIRouter()


@router.get("/contribuyente/{nit}/comportamiento", response_model=ComportamientoResponse)
async def analizar_comportamiento_contribuyente(
    nit: str,
    periodo: str = "2024",
    ciiu: str | None = None,
    regimen: str | None = None,
    min_pares: int = Query(10, ge=3, le=100),
):
    use_case = AnalizarComportamientoUseCase()
    return await use_case.analizar_nit(
        nit=nit,
        periodo=periodo,
        ciiu=ciiu,
        regimen=regimen,
        min_pares=min_pares,
    )


@router.get("/proceso/{proceso_id}/ranking-comportamental", response_model=RankingComportamentalResponse)
async def ranking_comportamental_proceso(
    proceso_id: uuid.UUID,
    periodo: str | None = None,
    limite: int = Query(50, ge=1, le=100),
    min_score: float = Query(0, ge=0, le=100),
    min_pares: int = Query(10, ge=3, le=100),
):
    use_case = AnalizarComportamientoUseCase()
    return await use_case.ranking_proceso(
        proceso_id=proceso_id,
        periodo=periodo,
        limite=limite,
        min_score=min_score,
        min_pares=min_pares,
    )


@router.get("/contribuyente/{nit}/grafo-riesgo", response_model=GrafoRiesgoResponse)
async def analizar_grafo_riesgo_contribuyente(
    nit: str,
    periodo: str = "2024",
    min_pares: int = Query(10, ge=3, le=100),
    incluir_comportamiento: bool = True,
):
    use_case = AnalizarGrafoRiesgoUseCase()
    return await use_case.analizar_nit(
        nit=nit,
        periodo=periodo,
        min_pares=min_pares,
        incluir_comportamiento=incluir_comportamiento,
    )


@router.get("/contribuyente/{nit}/expediente-fiscal", response_model=ExpedienteFiscalResponse)
async def generar_expediente_fiscal(
    nit: str,
    periodo: str = "2024",
    min_pares: int = Query(10, ge=3, le=100),
):
    use_case = GenerarExpedienteFiscalUseCase()
    return await use_case.generar(nit=nit, periodo=periodo, min_pares=min_pares)


@router.get("/visor/grafo/{nit}", response_class=HTMLResponse)
async def visor_grafo_riesgo(
    nit: str,
    periodo: str = "2024",
):
    return HTMLResponse(render_graph_viewer(nit=nit, periodo=periodo))
