from pydantic import BaseModel


class MCPNitResult(BaseModel):
    nit: str
    score_peso: float = 0.0
    es_candidato: bool = True
    razon: str = ""


class DatosFiscales(BaseModel):
    nit: str
    razon_social: str = ""
    ciiu: str = ""
    regimen: str = ""
    declaraciones_ica: list[dict] = []
    exogena_dian: list[dict] = []
    rues_estado: str = ""
    rues_fecha_constitucion: str | None = None


class HallazgoContribuyente(BaseModel):
    tipo: str
    severidad: str | None = None
    descripcion: str | None = None
    diferencia: float | None = None
    ciiu: str | None = None
    detalle: dict | None = None


class ComponenteSRF(BaseModel):
    nombre: str
    valor: float
    peso: float


class AnalyzeResponse(BaseModel):
    nit: str
    razon_social: str = ""
    ciiu: str = ""
    clasificacion: str = "PENDIENTE"
    mcp_score: float = 0.0
    mcp_razon: str = ""
    srf_total: float = 0.0
    componentes_srf: list[ComponenteSRF] = []
    nivel_riesgo: str = "BAJO"
    hallazgos: list[HallazgoContribuyente] = []
    explicacion_ia: str = ""
    tokens_utilizados: int = 0
    duracion_ms: int = 0
    provider_utilizado: str = ""
    cache_hit: bool = False
