from fastapi import Depends
from domain.ports.cruce_repo import CruceRepo
from domain.ports.inconsistencia_repo import InconsistenciaRepo
from domain.ports.analisis_repo import ScoreRepo, AnalisisRepo
from domain.ports.llm_port import LLMPort
from infrastructure.adapters.repos.oracle_cruce_repo import OracleCruceRepo
from infrastructure.adapters.repos.oracle_inconsistencia_repo import OracleInconsistenciaRepo
from infrastructure.adapters.repos.oracle_score_repo import OracleScoreRepo
from infrastructure.adapters.repos.oracle_analisis_repo import OracleAnalisisRepo
from infrastructure.adapters.llm.litellm_adapter import LiteLLMAdapter
from infrastructure.adapters.cache.memory_cache import MemoryCache
from application.use_cases.analizar_contribuyente import AnalizarContribuyente
from application.use_cases.calcular_score import CalcularScore


_cache_instance: MemoryCache = None


def get_cache() -> MemoryCache:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = MemoryCache()
    return _cache_instance


def get_cruce_repo() -> CruceRepo:
    return OracleCruceRepo()


def get_inconsistencia_repo() -> InconsistenciaRepo:
    return OracleInconsistenciaRepo()


def get_score_repo() -> ScoreRepo:
    return OracleScoreRepo()


def get_analisis_repo() -> AnalisisRepo:
    return OracleAnalisisRepo()


def get_llm() -> LLMPort:
    return LiteLLMAdapter()


def get_analizar_use_case(
    cruce_repo: CruceRepo = Depends(get_cruce_repo),
    inconsistencia_repo: InconsistenciaRepo = Depends(get_inconsistencia_repo),
    score_repo: ScoreRepo = Depends(get_score_repo),
    analisis_repo: AnalisisRepo = Depends(get_analisis_repo),
    llm: LLMPort = Depends(get_llm),
    cache: MemoryCache = Depends(get_cache),
) -> AnalizarContribuyente:
    return AnalizarContribuyente(cruce_repo, inconsistencia_repo, score_repo, analisis_repo, llm, cache)


def get_calcular_score_use_case(
    score_repo: ScoreRepo = Depends(get_score_repo),
    llm: LLMPort = Depends(get_llm),
    cache: MemoryCache = Depends(get_cache),
) -> CalcularScore:
    return CalcularScore(score_repo, llm, cache)
