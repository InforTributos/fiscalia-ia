from __future__ import annotations

import uuid

from application.use_cases.aplicar_reglas_fiscales import AplicarReglasFiscalesUseCase
from application.use_cases.construir_perfil_fiscal import construir_perfil_fiscal_desde_datos_originales
from application.use_cases.gestionar_hallazgos import GestionarHallazgosUseCase
from application.use_cases.revisar_hallazgo_agente import RevisarHallazgoAgenteUseCase
from domain.errors import NITNoEncontradoError
from fastapi import APIRouter, Query
from infrastructure.mcp.oracle_adapter import OracleClient
from infrastructure.mcp.pagination import obtener_datos_fiscales
from schemas.fiscalizacion import (
    CrearHallazgoRequest,
    EvaluacionReglasResponse,
    HallazgoResponse,
    ListaHallazgosResponse,
    PerfilFiscalRequest,
    RevisionAgenteRequest,
    RevisionAgenteResponse,
    RevisionRequest,
)

router = APIRouter()


@router.post("/fiscalizacion/reglas/evaluar", response_model=EvaluacionReglasResponse)
async def evaluar_reglas_fiscales(request: PerfilFiscalRequest):
    payload = request.model_dump()
    reglas = payload.pop("reglas", None)
    resultados = await AplicarReglasFiscalesUseCase().evaluar(payload, reglas=reglas)
    return {"total": len(resultados), "resultados": resultados}


@router.post("/fiscalizacion/reglas/evaluar/{contribuyente_nit}", response_model=EvaluacionReglasResponse)
async def evaluar_reglas_fiscales_por_nit(
    contribuyente_nit: str,
    periodo: str = "2024",
    reglas: list[str] | None = Query(None),
):
    perfil = await _perfil_desde_contrato_original(contribuyente_nit=contribuyente_nit, periodo=periodo, reglas=reglas)
    resultados = await AplicarReglasFiscalesUseCase().evaluar(perfil, reglas=reglas)
    return {"total": len(resultados), "resultados": resultados}


@router.post("/fiscalizacion/reglas/ejecutar", response_model=list[HallazgoResponse], status_code=201)
async def ejecutar_reglas_fiscales(
    request: PerfilFiscalRequest,
    proceso_id: uuid.UUID | None = None,
    entidad_id: uuid.UUID | None = None,
):
    payload = request.model_dump()
    reglas = payload.pop("reglas", None)
    return await AplicarReglasFiscalesUseCase().ejecutar(
        payload, reglas=reglas, proceso_id=proceso_id, entidad_id=entidad_id,
    )


@router.post("/fiscalizacion/reglas/ejecutar/{contribuyente_nit}", response_model=list[HallazgoResponse], status_code=201)
async def ejecutar_reglas_fiscales_por_nit(
    contribuyente_nit: str,
    periodo: str = "2024",
    reglas: list[str] | None = Query(None),
    proceso_id: uuid.UUID | None = None,
    entidad_id: uuid.UUID | None = None,
):
    perfil = await _perfil_desde_contrato_original(contribuyente_nit=contribuyente_nit, periodo=periodo, reglas=reglas)
    return await AplicarReglasFiscalesUseCase().ejecutar(
        perfil, reglas=reglas, proceso_id=proceso_id, entidad_id=entidad_id,
    )


@router.post("/fiscalizacion/hallazgos", response_model=HallazgoResponse, status_code=201)
async def crear_hallazgo(request: CrearHallazgoRequest):
    return await GestionarHallazgosUseCase().crear_hallazgo(request.model_dump())


@router.post("/fiscalizacion/hallazgos/desde-grafo/{contribuyente_nit}", response_model=HallazgoResponse, status_code=201)
async def crear_hallazgo_desde_grafo(
    contribuyente_nit: str,
    periodo: str = "2024",
    min_pares: int = Query(10, ge=3, le=100),
):
    return await GestionarHallazgosUseCase().crear_desde_grafo(contribuyente_nit=contribuyente_nit, periodo=periodo, min_pares=min_pares)


@router.get("/fiscalizacion/hallazgos", response_model=ListaHallazgosResponse)
async def listar_hallazgos(
    estado: str | None = None,
    regla: str | None = None,
    contribuyente_nit: str | None = None,
    accionable: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    total, rows = await GestionarHallazgosUseCase().listar(
        estado=estado,
        regla=regla,
        nit=contribuyente_nit,
        accionable=accionable,
        page=page,
        page_size=page_size,
    )
    return {"total": total, "page": page, "page_size": page_size, "resultados": rows}


@router.get("/fiscalizacion/hallazgos/{hallazgo_id}", response_model=HallazgoResponse)
async def obtener_hallazgo(hallazgo_id: uuid.UUID):
    return await GestionarHallazgosUseCase().obtener(hallazgo_id)


@router.post("/fiscalizacion/hallazgos/{hallazgo_id}/revision", response_model=HallazgoResponse)
async def revisar_hallazgo(hallazgo_id: uuid.UUID, request: RevisionRequest):
    return await GestionarHallazgosUseCase().revisar(
        hallazgo_id=hallazgo_id,
        funcionario_id=request.funcionario_id,
        decision=request.decision,
        motivo=request.motivo,
    )


@router.post("/fiscalizacion/hallazgos/{hallazgo_id}/revision-agente", response_model=RevisionAgenteResponse)
async def revisar_hallazgo_con_agente(hallazgo_id: uuid.UUID, request: RevisionAgenteRequest):
    return await RevisarHallazgoAgenteUseCase().revisar(
        hallazgo_id=hallazgo_id,
        usar_ia=request.usar_ia,
    )


async def _perfil_desde_contrato_original(contribuyente_nit: str, periodo: str, reglas: list[str] | None = None) -> dict:
    client = OracleClient()
    datos = await obtener_datos_fiscales(client, contribuyente_nit, periodo)
    if not datos:
        raise NITNoEncontradoError(contribuyente_nit)
    return construir_perfil_fiscal_desde_datos_originales(datos, periodo=periodo, reglas=reglas)
