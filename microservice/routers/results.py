import uuid

from domain.errors import ProcesoNoEncontradoError, ProcesoEnProcesoError
from fastapi import APIRouter, Query
from infrastructure.persistence.repositorio_proceso import PostgresProcesoRepo
from schemas.results import ResultsResponse, Paginacion, ResultadoDetalle, HallazgoResult

router = APIRouter()
repo = PostgresProcesoRepo()


@router.get("/proceso/{proceso_id}/results", response_model=ResultsResponse)
async def consultar_resultados(
    proceso_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    intento_id: int | None = None,
    include_partial: bool = False,
    clasificacion: str | None = None,
    min_score: float | None = None,
    ordenar_por: str = "mcp_score",
    direccion: str = "desc",
):
    proceso = await repo.obtener_proceso(proceso_id)
    if not proceso:
        raise ProcesoNoEncontradoError(str(proceso_id))

    if not include_partial and proceso["estado"] not in ("COMPLETADO", "ERROR", "INTERRUMPIDO"):
        raise ProcesoEnProcesoError(
            str(proceso_id),
            mensaje=f"El proceso aún no ha terminado (estado: {proceso['estado']}). Use include_partial=true para ver resultados parciales.",
        )

    total, rows = await repo.listar_proceso_detalle(
        proceso_id=proceso_id, intento_id=intento_id,
        page=page, page_size=page_size,
        clasificacion=clasificacion, min_score=min_score,
        ordenar_por=ordenar_por, direccion=direccion,
    )

    resultados = []
    for r in rows:
        hallazgos_raw = r.get("hallazgos") or []
        if isinstance(hallazgos_raw, str):
            import json
            hallazgos_raw = json.loads(hallazgos_raw)
        hallazgos = [
            HallazgoResult(**h) if isinstance(h, dict) else HallazgoResult(tipo=str(h))
            for h in hallazgos_raw
        ]

        resultados.append(ResultadoDetalle(
            nit=r["nit"],
            razon_social=r.get("razon_social"),
            ciiu=r.get("ciiu"),
            clasificacion=r["clasificacion"],
            mcp_score=float(r["mcp_score"]) if r.get("mcp_score") else None,
            mcp_razon=r.get("mcp_razon"),
            srf_total=float(r["srf_total"]) if r.get("srf_total") else None,
            nivel_riesgo=r.get("nivel_riesgo"),
            hallazgos=hallazgos,
            explicacion_ia=r.get("explicacion_ia"),
        ))

    return ResultsResponse(
        proceso_id=proceso_id,
        estado=proceso["estado"],
        intento_id=intento_id,
        parcial=proceso["estado"] not in ("COMPLETADO", "ERROR", "INTERRUMPIDO"),
        paginacion=Paginacion(
            page=page,
            page_size=page_size,
            total_registros=total,
            total_paginas=max(1, (total + page_size - 1) // page_size),
        ),
        resultados=resultados,
    )
