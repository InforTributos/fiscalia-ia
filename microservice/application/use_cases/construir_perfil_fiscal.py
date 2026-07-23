from __future__ import annotations

from domain.services.crosscheck_service import _tarifas_ciiu


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

    # Build retenciones_ica from our extended data (unblocks R1)
    ret_practicadas = _num(datos.get("retenciones_declaradas_practicadas", 0))
    exo_practicadas = _num(datos.get("retenciones_exogena_practicadas", 0))
    retenciones_ica = []
    if ret_practicadas > 0 or exo_practicadas > 0:
        retenciones_ica = [{"valor_retenido": max(ret_practicadas, exo_practicadas)}]

    # Determine tarifa correcta from official registry (unblocks R7)
    ciiu = datos.get("ciiu", "")
    tarifa_correcta = _tarifas_ciiu.get(ciiu)
    tarifa_retencion = tarifa_correcta or 0.01

    # R9: compute ingresos_locales_no_declarados from exogena vs declared base
    total_exogena_ingresos = sum(_num(row.get("ingresos", row.get("valor"))) for row in exogena)
    total_base_declarada = sum(_num(row.get("base_gravable")) for row in declaraciones)
    ingresos_locales_no_declarados = max(total_exogena_ingresos - total_base_declarada, 0.0)
    evidencia_territorialidad = {}
    if ingresos_locales_no_declarados > 0:
        evidencia_territorialidad = {
            "ingresos_exogena": total_exogena_ingresos,
            "base_declarada": total_base_declarada,
            "diferencia": ingresos_locales_no_declarados,
        }

    # Extract tarifa_declarada from first declaration that has it
    tarifa_declarada = 0.0
    for dec in declaraciones:
        td = _num(dec.get("tarifa_declarada", dec.get("tarifa", 0)))
        if td > 0:
            tarifa_declarada = td
            break

    perfil = {
        "contribuyente_nit": datos.get("contribuyente_nit", ""),
        "periodo": periodo,
        "reglas": reglas,
        "razon_social": datos.get("razon_social", ""),
        "ciiu": ciiu,
        "regimen": datos.get("regimen", ""),
        "declaraciones_ica": declaraciones,
        "retenciones_ica": retenciones_ica,
        "tarifa_retencion": tarifa_retencion,
        "tarifa_correcta": tarifa_correcta,
        "tarifa_declarada": tarifa_declarada,
        "exogena_dian": exogena,
        "facturacion_electronica": _lista(datos.get("facturacion_electronica")),
        "contratos_publicos": _lista(datos.get("contratos_publicos")),
        "senales_actividad": senales_actividad,
        "historico_bases": _historico_bases(declaraciones, periodo),
        "presencia_registral": presencia_registral,
        "vinculo_local": presencia_registral,
        "ingresos_locales_no_declarados": ingresos_locales_no_declarados,
        "evidencia_territorialidad": evidencia_territorialidad,
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
