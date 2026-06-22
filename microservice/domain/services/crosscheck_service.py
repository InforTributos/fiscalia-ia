import logging

logger = logging.getLogger(__name__)

PESO_EXOGENA = 35
PESO_OMISION = 20
PESO_TARIFA = 25
PESO_RUES = 20

TARIFAS_CIIU = {
    "4711": 0.008,
    "4712": 0.008,
    "4721": 0.006,
    "5611": 0.010,
    "6820": 0.005,
    "8511": 0.004,
    "6201": 0.003,
    "6202": 0.003,
}


def clasificar_por_datos(datos: dict) -> str:
    declaraciones = datos.get("declaraciones_ica", [])
    if not declaraciones:
        return "OMISO"
    return "INEXACTO"


def extraer_inconsistencias(datos: dict) -> list[dict]:
    inconsistencias = []
    exogena_list = datos.get("exogena_dian", [])
    ingresos_exogena = sum(e.get("ingresos", 0) or 0 for e in exogena_list)

    for dec in datos.get("declaraciones_ica", []):
        base = dec.get("base_gravable", 0) or 0
        if base == 0:
            inconsistencias.append({"tipo": "BASE_CERO", "periodo": dec.get("periodo"), "severidad": "MEDIA"})

        ciiu = datos.get("ciiu", "")
        tarifa_oficial = TARIFAS_CIIU.get(ciiu)
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
    tarifa_oficial = TARIFAS_CIIU.get(ciiu)
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
