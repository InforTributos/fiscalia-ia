from __future__ import annotations


def construir_perfil_fiscal_desde_datos_originales(
    datos: dict,
    periodo: str,
    reglas: list[str] | None = None,
) -> dict:
    declaraciones = _lista(datos.get("declaraciones_ica"))
    exogena = _lista(datos.get("exogena_dian"))
    rues_estado = str(datos.get("rues_estado") or "").upper()
    presencia_registral = bool(rues_estado and rues_estado not in {"CANCELADO", "INACTIVO"})

    senales_actividad = []
    if exogena:
        senales_actividad.append({
            "fuente": "EXOGENA_DIAN",
            "descripcion": "Existen ingresos reportados por informacion exogena.",
            "valor": sum(_num(row.get("ingresos", row.get("valor"))) for row in exogena),
        })

    perfil = {
        "nit": datos.get("nit", ""),
        "periodo": periodo,
        "reglas": reglas,
        "razon_social": datos.get("razon_social", ""),
        "ciiu": datos.get("ciiu", ""),
        "regimen": datos.get("regimen", ""),
        "declaraciones_ica": declaraciones,
        "retenciones_ica": _lista(datos.get("retenciones_ica")),
        "exogena_dian": exogena,
        "facturacion_electronica": _lista(datos.get("facturacion_electronica")),
        "contratos_publicos": _lista(datos.get("contratos_publicos")),
        "senales_actividad": senales_actividad,
        "historico_bases": _historico_bases(declaraciones, periodo),
        "presencia_registral": presencia_registral,
        "vinculo_local": presencia_registral,
        "metadata": {
            "origen": "CONTRATO_ORIGINAL",
            "rues_estado": datos.get("rues_estado", ""),
            "datos_originales": datos,
        },
    }
    return perfil


def _lista(value) -> list[dict]:
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    return []


def _historico_bases(declaraciones: list[dict], periodo: str) -> list[dict]:
    historico = []
    for row in declaraciones:
        historico.append({
            "periodo": str(row.get("periodo", periodo)),
            "base_gravable": _num(row.get("base_gravable")),
        })
    return historico


def _num(value, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
