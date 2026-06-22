import logging

logger = logging.getLogger(__name__)


def clasificar_nit(mcp_item: dict) -> tuple[str, str]:
    """Clasifica un NIT en OMISO, EXACTO o INEXACTO basado en datos MCP.

    Returns:
        tuple[str, str]: (clasificacion, detalle_clasificacion)
    """
    es_candidato = mcp_item.get("es_candidato", False)

    if not es_candidato:
        return ("EXACTO", "Contribuyente sin alertas — declaración correcta")

    score = mcp_item.get("score_peso", 0)
    razon = mcp_item.get("razon", "")

    if _es_omiso(mcp_item):
        return ("OMISO", razon or "No se encontraron declaraciones ICA para el período")

    if score >= 30:
        return ("INEXACTO", razon or f"Diferencia significativa detectada (score: {score})")

    return ("EXACTO", "Sin inconsistencias relevantes")


def _es_omiso(item: dict) -> bool:
    if item.get("es_omiso"):
        return True
    razon = (item.get("razon") or "").lower()
    keywords = ["omiso", "no declaró", "sin declaración", "no presenta", "omisión"]
    return any(kw in razon for kw in keywords)
