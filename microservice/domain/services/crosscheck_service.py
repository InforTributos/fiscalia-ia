import logging

logger = logging.getLogger(__name__)

PESO_EXOGENA = 35
PESO_OMISION = 20
PESO_TARIFA = 25
PESO_RUES = 20

TARIFAS_CIIU_DEFAULT = {
    "4711": 0.008,
    "4712": 0.008,
    "4721": 0.006,
    "5611": 0.010,
    "6820": 0.005,
    "8511": 0.004,
    "6201": 0.003,
    "6202": 0.003,
}

_tarifas_ciiu: dict[str, float] = dict(TARIFAS_CIIU_DEFAULT)


def configurar_tarifas(tarifas: dict[str, float]):
    _tarifas_ciiu.clear()
    _tarifas_ciiu.update(tarifas)


def clasificar_por_datos(datos: dict) -> str:
    tipo = datos.get("tipo", "")
    if tipo in ("OMISO_CONOCIDO", "OMISO_DESCONOCIDO", "INEXACTO_CIIU", "INEXACTO_RETENCIONES"):
        return tipo

    declaraciones = datos.get("declaraciones_ica", [])
    if not declaraciones:
        return "OMISO"
    return "INEXACTO"


def extraer_inconsistencias(datos: dict) -> list[dict]:
    inconsistencias = []

    # --- CIIU vs DIAN check (data-driven, unconditional if data present) ---
    ciiu_dec = datos.get("ciiu_declarado", datos.get("ciiu", ""))
    ciiu_dian = datos.get("ciiu_dian", "")
    if ciiu_dec and ciiu_dian and ciiu_dec != ciiu_dian:
        tarifa_dec = datos.get("tarifa_declarada", 0) or 0
        tarifa_dian = datos.get("tarifa_dian", 0) or 0
        if tarifa_dian > tarifa_dec:
            inconsistencias.append({
                "tipo": "TARIFA_INCORRECTA_CIIU",
                "ciiu_declarado": ciiu_dec,
                "ciiu_dian": ciiu_dian,
                "tarifa_declarada": tarifa_dec,
                "tarifa_dian": tarifa_dian,
                "severidad": "ALTA",
            })

    # --- Retenciones check (data-driven, unconditional if data present) ---
    ret_practicadas = datos.get("retenciones_declaradas_practicadas", 0) or 0
    exo_practicadas = datos.get("retenciones_exogena_practicadas", 0) or 0
    diff_pct = datos.get("diferencia_pct", 0) or 0
    if ret_practicadas > 0 and exo_practicadas > 0 and diff_pct > 0:
        inconsistencias.append({
            "tipo": "RETENCIONES_INCONSISTENTES",
            "diferencia_pct": diff_pct,
            "retenciones_declaradas_practicadas": ret_practicadas,
            "retenciones_exogena_practicadas": exo_practicadas,
            "severidad": "MEDIA" if diff_pct < 20 else "ALTA",
        })

    # --- Generic checks (always run) ---
    exogena_list = datos.get("exogena_dian", [])
    ingresos_exogena = sum(e.get("ingresos", 0) or 0 for e in exogena_list)

    for dec in datos.get("declaraciones_ica", []):
        base = dec.get("base_gravable", 0) or 0
        if base == 0:
            inconsistencias.append({"tipo": "BASE_CERO", "periodo": dec.get("periodo"), "severidad": "MEDIA"})

        ciiu = datos.get("ciiu", "")
        tarifa_oficial = _tarifas_ciiu.get(ciiu)
        tarifa_declarada = dec.get("tarifa", 0) or 0
        if tarifa_oficial and tarifa_declarada > 0 and abs(tarifa_declarada - tarifa_oficial) > 0.001:
            inconsistencias.append({
                "tipo": "TARIFA_INCORRECTA",
                "periodo": dec.get("periodo"),
                "tarifa_declarada": tarifa_declarada,
                "tarifa_oficial": tarifa_oficial,
                "severidad": "MEDIA",
            })

    if ingresos_exogena > 0:
        total_declarado = sum(d.get("base_gravable", 0) or 0 for d in datos.get("declaraciones_ica", []))
        if total_declarado > 0 and ingresos_exogena > total_declarado * 1.15:
            inconsistencias.append({
                "tipo": "SUBDECLARACION_EXOGENA",
                "declarado": total_declarado,
                "exogena": ingresos_exogena,
                "diferencia": ingresos_exogena - total_declarado,
                "variacion_pct": round((ingresos_exogena - total_declarado) / total_declarado * 100, 1),
                "severidad": "ALTA",
            })

    return inconsistencias


def calcular_srf(datos: dict) -> dict:
    componentes = {}
    score = 0.0

    ingresos_exogena = sum(e.get("ingresos", 0) or 0 for e in datos.get("exogena_dian", []))
    declaraciones = datos.get("declaraciones_ica", [])
    total_declarado = sum(d.get("base_gravable", 0) or 0 for d in declaraciones)

    if ingresos_exogena > 0 and total_declarado > 0:
        diff_pct = (ingresos_exogena - total_declarado) / total_declarado
        comp_exogena = min(diff_pct * PESO_EXOGENA, PESO_EXOGENA) if diff_pct > 0.15 else 0
    else:
        comp_exogena = 0
    componentes["diferencia_exogena"] = {"valor": comp_exogena, "peso": PESO_EXOGENA, "nombre": "Diferencia exógena vs ICA"}
    score += comp_exogena

    if not declaraciones:
        comp_omision = PESO_OMISION
    else:
        periodos_esperados = 6
        periodos_reales = len(declaraciones)
        comp_omision = max(0, (periodos_esperados - periodos_reales) / periodos_esperados * PESO_OMISION)
    componentes["antiguedad_omision"] = {"valor": comp_omision, "peso": PESO_OMISION, "nombre": "Antigüedad sin declarar"}
    score += comp_omision

    ciiu = datos.get("ciiu", "")
    tarifa_oficial = _tarifas_ciiu.get(ciiu)
    if tarifa_oficial and declaraciones:
        discrepancias = []
        for dec in declaraciones:
            tarifa_dec = dec.get("tarifa", 0) or 0
            if tarifa_dec > 0:
                discrepancias.append(abs(tarifa_dec - tarifa_oficial))
        comp_tarifa = min(max(discrepancias) * PESO_TARIFA * 10, PESO_TARIFA) if discrepancias else 0
    else:
        comp_tarifa = 0
    componentes["discrepancia_tarifa"] = {"valor": comp_tarifa, "peso": PESO_TARIFA, "nombre": "Discrepancia tarifa CIIU"}
    score += comp_tarifa

    rues = datos.get("rues_estado", "").upper()
    if rues == "INACTIVO" or rues == "SUSPENDIDO":
        comp_rues = PESO_RUES
    elif rues == "" or rues is None:
        comp_rues = PESO_RUES * 0.5
    else:
        comp_rues = 0
    componentes["estado_rues"] = {"valor": comp_rues, "peso": PESO_RUES, "nombre": "Estado RUES vs padrón"}
    score += comp_rues

    return {
        "srf_total": round(min(score, 100), 2),
        "componentes": componentes,
    }
