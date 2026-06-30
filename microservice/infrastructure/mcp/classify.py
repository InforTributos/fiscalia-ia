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


def clasificar_candidato(item: dict) -> tuple[str, str]:
    tipo = item.get("tipo", "")

    if tipo == "OMISO_CONOCIDO":
        razon = item.get("razon", "Contribuyente registrado sin declaracion ICA")
        return ("OMISO_CONOCIDO", razon)

    if tipo == "OMISO_DESCONOCIDO":
        fuente = item.get("fuente", "externa")
        return ("OMISO_DESCONOCIDO", f"Detectado por fuente {fuente} — no registrado en el municipio")

    if tipo == "INEXACTO_CIIU":
        ciiu_dec = item.get("ciiu_declarado", "")
        ciiu_dian = item.get("ciiu_dian", "")
        return ("INEXACTO_CIIU", f"CIIU declarado {ciiu_dec} vs DIAN {ciiu_dian}")

    if tipo == "INEXACTO_RETENCIONES":
        diff = item.get("diferencia_pct", 0)
        return ("INEXACTO_RETENCIONES", f"Diferencia en retenciones del {diff}%")

    return ("EXACTO", "Sin inconsistencias detectadas")
