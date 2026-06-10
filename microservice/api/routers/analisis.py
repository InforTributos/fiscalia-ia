from fastapi import APIRouter, Depends
from api.deps import get_analizar_use_case
from application.use_cases.analizar_contribuyente import AnalizarContribuyente, AnalisisDTO

router = APIRouter()


@router.post(
    "/analizar/{nit}",
    response_model=AnalisisDTO,
    summary="Análisis completo de fiscalización para un contribuyente",
)
async def analizar_contribuyente(
    nit: str,
    periodo: str = "2025-01",
    use_case: AnalizarContribuyente = Depends(get_analizar_use_case),
):
    return await use_case.ejecutar(nit, periodo)
