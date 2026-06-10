from application.use_cases.analizar_contribuyente import AnalisisDTO, AnalizarContribuyente
from fastapi import APIRouter, Depends

from api.deps import get_analizar_use_case
from api.middleware.auth import AuthDep

router = APIRouter()


@router.post(
    "/analizar/{nit}",
    response_model=AnalisisDTO,
    summary="Análisis completo de fiscalización para un contribuyente",
    dependencies=[AuthDep],
)
async def analizar_contribuyente(
    nit: str,
    periodo: str = "2025-01",
    use_case: AnalizarContribuyente = Depends(get_analizar_use_case),
):
    return await use_case.ejecutar(nit, periodo)
