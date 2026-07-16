from __future__ import annotations

from domain.fiscalizacion.rules_catalog import obtener_regla


def evaluar_reglas(perfil: dict, reglas: list[str] | None = None) -> list[dict]:
    reglas_ref = reglas or [f"R{i}" for i in range(1, 11)]
    evaluadores = {
        "R1": _evaluar_r1,
        "R2": _evaluar_r2,
        "R3": _evaluar_r3,
        "R4": _evaluar_r4,
        "R5": _evaluar_r5,
        "R6": _evaluar_r6,
        "R7": _evaluar_r7,
        "R8": _evaluar_r8,
        "R9": _evaluar_r9,
        "R10": _evaluar_r10,
    }
    hallazgos = []
    for codigo in reglas_ref:
        if codigo not in evaluadores:
            obtener_regla(codigo)
        result = evaluadores[codigo](perfil)
        if result:
            hallazgos.append(result)
    return hallazgos


def _base_declarada(perfil: dict) -> float:
    return sum(_num(d.get("base_gravable")) for d in perfil.get("declaraciones_ica", []))


def _impuesto_declarado(perfil: dict) -> float:
    return sum(_num(d.get("impuesto")) for d in perfil.get("declaraciones_ica", []))


def _tiene_declaracion(perfil: dict) -> bool:
    return bool(perfil.get("declaraciones_ica"))


def _evaluar_r1(perfil: dict) -> dict | None:
    retenciones = perfil.get("retenciones_ica", [])
    total_retenciones = sum(_num(r.get("valor_retenido", r.get("retencion"))) for r in retenciones)
    if total_retenciones <= 0:
        return None
    tarifa = _num(perfil.get("tarifa_retencion"), 0.01) or 0.01
    tolerancia = _num(perfil.get("tolerancia"), 0.05)
    ingresos_minimos = total_retenciones / tarifa
    base = _base_declarada(perfil)
    if not _tiene_declaracion(perfil):
        return _hallazgo(perfil, "R1", "OMISO", ingresos_minimos, total_retenciones, "Retenciones ICA sin declaracion.", retenciones)
    if base < ingresos_minimos * (1 - tolerancia):
        return _hallazgo(perfil, "R1", "INEXACTO", ingresos_minimos - base, total_retenciones, "Base declarada inferior a ingresos minimos por retenciones.", retenciones)
    return None


def _evaluar_r2(perfil: dict) -> dict | None:
    if _tiene_declaracion(perfil):
        return None
    presencia = bool(perfil.get("presencia_registral") or perfil.get("rit_activo") or perfil.get("matricula_activa"))
    senales = perfil.get("senales_actividad", [])
    if presencia and senales:
        impuesto = _num(perfil.get("impuesto_presuntivo"))
        return _hallazgo(perfil, "R2", "OMISO", _num(perfil.get("base_presuntiva")), impuesto, "Presencia registral con senales de actividad y sin declaracion.", senales)
    return None


def _evaluar_r3(perfil: dict) -> dict | None:
    ingresos = sum(_num(e.get("ingresos", e.get("valor"))) for e in perfil.get("exogena_dian", []))
    base = _base_declarada(perfil)
    if ingresos <= 0:
        return None
    vinculo_local = bool(perfil.get("vinculo_local") or perfil.get("unico_establecimiento") or perfil.get("presencia_registral"))
    if not vinculo_local:
        return None
    threshold = _num(perfil.get("umbral_exogena"), 0.15)
    if not _tiene_declaracion(perfil):
        return _hallazgo(perfil, "R3", "OMISO", ingresos, 0, "Ingresos exogenos con vinculo local y sin declaracion ICA.", perfil.get("exogena_dian", []))
    if ingresos > base * (1 + threshold):
        return _hallazgo(perfil, "R3", "INEXACTO", ingresos - base, 0, "Brecha entre exogena DIAN y base ICA declarada.", perfil.get("exogena_dian", []))
    return None


def _evaluar_r4(perfil: dict) -> dict | None:
    facturas = perfil.get("facturacion_electronica", [])
    total_local = sum(_num(f.get("valor", f.get("monto"))) for f in facturas if f.get("local", True))
    if total_local <= 0:
        return None
    base = _base_declarada(perfil)
    tolerancia = _num(perfil.get("tolerancia"), 0.05)
    if not _tiene_declaracion(perfil):
        return _hallazgo(perfil, "R4", "OMISO", total_local, 0, "Facturacion electronica local sin declaracion ICA.", facturas)
    if base < total_local * (1 - tolerancia):
        return _hallazgo(perfil, "R4", "INEXACTO", total_local - base, 0, "Base declarada inferior a facturacion electronica local.", facturas)
    return None


def _evaluar_r5(perfil: dict) -> dict | None:
    contratos = perfil.get("contratos_publicos", [])
    total = sum(_num(c.get("valor", c.get("monto"))) for c in contratos)
    if total <= 0:
        return None
    base = _base_declarada(perfil)
    if not _tiene_declaracion(perfil):
        return _hallazgo(perfil, "R5", "OMISO", total, 0, "Contratos estatales con ejecucion local sin declaracion ICA.", contratos)
    if total > base * 1.15:
        return _hallazgo(perfil, "R5", "INEXACTO", total - base, 0, "Contratos estatales superiores a la base ICA declarada.", contratos)
    return None


def _evaluar_r6(perfil: dict) -> dict | None:
    declaraciones = perfil.get("declaraciones_ica", [])
    if not declaraciones:
        return None
    ceros = sum(1 for d in declaraciones if _num(d.get("base_gravable")) <= 0)
    senales = perfil.get("senales_actividad", [])
    if ceros >= _num(perfil.get("periodos_cero_minimos"), 2) and senales:
        return _hallazgo(perfil, "R6", "INEXACTO_INDICIARIO", 0, 0, "Declaraciones en cero persistentes con senales de actividad.", senales)
    return None


def _evaluar_r7(perfil: dict) -> dict | None:
    tarifa_declarada = _num(perfil.get("tarifa_declarada"))
    tarifa_correcta = _num(perfil.get("tarifa_correcta"))
    base = _base_declarada(perfil)
    if tarifa_correcta > tarifa_declarada > 0 and base > 0:
        impuesto = base * (tarifa_correcta - tarifa_declarada)
        return _hallazgo(perfil, "R7", "INEXACTO", base, impuesto, "Tarifa CIIU declarada inferior a tarifa predominante/correcta.", {"tarifa_declarada": tarifa_declarada, "tarifa_correcta": tarifa_correcta})
    return None


def _evaluar_r8(perfil: dict) -> dict | None:
    indicadores = perfil.get("indicadores_sectoriales", {})
    bajos = [k for k, v in indicadores.items() if _num(v.get("percentil"), 100) <= 10]
    if perfil.get("atipico_sectorial") or len(bajos) >= 2:
        return _hallazgo(perfil, "R8", "INEXACTO_INDICIARIO", 0, 0, "Contribuyente atipico frente a su grupo comparable.", indicadores)
    return None


def _evaluar_r9(perfil: dict) -> dict | None:
    ingresos_locales_no_declarados = _num(perfil.get("ingresos_locales_no_declarados"))
    if ingresos_locales_no_declarados > 0:
        return _hallazgo(perfil, "R9", "INEXACTO", ingresos_locales_no_declarados, 0, "Posible ingreso local declarado o atribuido a otro municipio.", perfil.get("evidencia_territorialidad", {}))
    return None


def _evaluar_r10(perfil: dict) -> dict | None:
    historico = sorted(perfil.get("historico_bases", []), key=lambda x: str(x.get("periodo", "")))
    if len(historico) < 2:
        return None
    anterior = _num(historico[-2].get("base_gravable"))
    actual = _num(historico[-1].get("base_gravable"))
    if anterior > 0 and actual < anterior * (1 - _num(perfil.get("umbral_caida"), 0.6)):
        return _hallazgo(perfil, "R10", "INEXACTO_INDICIARIO", anterior - actual, 0, "Caida abrupta de base gravable frente al periodo anterior.", historico[-2:])
    return None


def _hallazgo(perfil: dict, regla: str, tipo: str, brecha: float, impuesto: float, resumen: str, evidencia) -> dict:
    catalog = obtener_regla(regla)
    return {
        "contribuyente_nit": perfil["contribuyente_nit"],
        "regla": regla,
        "periodo": perfil["periodo"],
        "tipo_hallazgo": tipo,
        "fuerza_probatoria": catalog.fuerza_probatoria,
        "brecha_valor": round(float(brecha or 0), 2),
        "impuesto_estimado": round(float(impuesto or 0), 2),
        "resumen": resumen,
        "evidencias": [{
            "fuente": catalog.nombre.upper().replace(" ", "_"),
            "referencia_registro": f"{perfil['contribuyente_nit']}:{perfil['periodo']}:{regla}",
            "descripcion": resumen,
            "snapshot": evidencia if isinstance(evidencia, dict) else {"items": evidencia},
        }],
    }


def _num(value, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

