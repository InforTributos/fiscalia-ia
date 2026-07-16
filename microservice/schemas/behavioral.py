from __future__ import annotations

from pydantic import BaseModel, Field


class MetricasContribuyente(BaseModel):
    contribuyente_nit: str
    razon_social: str = ""
    ciiu: str = ""
    regimen: str = ""
    vigencia: str
    base_gravable: float
    impuesto: float
    ingresos_exogena: float
    tarifa_efectiva: float | None = None
    ratio_exogena_declarado: float | None = None


class BenchmarkActividad(BaseModel):
    ciiu: str
    regimen: str = ""
    vigencia: str
    total_pares: int
    mediana_base_gravable: float
    p10_base_gravable: float
    p25_base_gravable: float
    p75_base_gravable: float
    p90_base_gravable: float
    mediana_tarifa_efectiva: float
    mediana_ratio_exogena_declarado: float


class DesviacionesComportamiento(BaseModel):
    percentil_base_gravable: float
    variacion_mediana_base_pct: float
    zscore_robusto_base: float
    outlier_iqr_inferior: bool


class HallazgoComportamental(BaseModel):
    tipo: str
    severidad: str
    descripcion: str
    evidencia: dict = Field(default_factory=dict)


class ComportamientoResponse(BaseModel):
    contribuyente_nit: str
    razon_social: str
    ciiu: str
    regimen: str
    vigencia: str
    score_comportamental: float
    prioridad: str
    confianza: float
    metricas: MetricasContribuyente
    benchmark: BenchmarkActividad
    desviaciones: DesviacionesComportamiento
    hallazgos: list[HallazgoComportamental]
    explicacion: str


class RankingError(BaseModel):
    contribuyente_nit: str
    mensaje: str


class RankingComportamentalResponse(BaseModel):
    proceso_id: str
    periodo: str
    total_evaluados: int
    total_rankeados: int
    errores: list[RankingError]
    resultados: list[ComportamientoResponse]


class GraphNodeResponse(BaseModel):
    id: str
    tipo: str
    label: str
    propiedades: dict = Field(default_factory=dict)


class GraphEdgeResponse(BaseModel):
    source: str
    target: str
    tipo: str
    peso: float
    evidencia: dict = Field(default_factory=dict)


class ResumenRiesgoRed(BaseModel):
    score_red: float
    score_comportamental: float
    bonus_red: float
    nivel_red: str
    empresas_conectadas: int
    motivos: list[str]


class GrafoRiesgoResponse(BaseModel):
    contribuyente_nit: str
    periodo: str
    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]
    resumen_red: ResumenRiesgoRed
    analisis_comportamental: ComportamientoResponse | None = None


class ScoreFiscalUnificado(BaseModel):
    score_fiscal_unificado: float
    prioridad: str
    componentes: dict = Field(default_factory=dict)
    criterios: list[str]


class ExpedienteFiscalResponse(BaseModel):
    contribuyente_nit: str
    periodo: str
    generado_en: str
    score: ScoreFiscalUnificado
    resumen_ejecutivo: str
    evidencia: list[str]
    acciones_sugeridas: list[str]
    grafo: dict = Field(default_factory=dict)
    analisis_comportamental: dict = Field(default_factory=dict)
    markdown: str
