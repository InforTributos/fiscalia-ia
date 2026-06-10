from application.use_cases.calcular_score import CalcularScore, ScoreDTO
from fastapi import APIRouter, Depends

from api.deps import get_calcular_score_use_case

router = APIRouter()


@router.post(
    "/score/{nit}",
    response_model=ScoreDTO,
    summary="Score de Riesgo Fiscal para un contribuyente",
)
async def score_contribuyente(
    nit: str,
    periodo: str = "2025-01",
    use_case: CalcularScore = Depends(get_calcular_score_use_case),
):
    return await use_case.ejecutar(nit, periodo)
