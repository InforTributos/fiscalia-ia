from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReglaFiscal:
    codigo: str
    nombre: str
    detecta: str
    fuerza_probatoria: str
    descripcion: str


RULES: dict[str, ReglaFiscal] = {
    "R1": ReglaFiscal("R1", "Retencion sin declaracion suficiente", "OMISO_INEXACTO", "DIRECTA", "Cruza retenciones ICA contra declaracion."),
    "R2": ReglaFiscal("R2", "Omiso con presencia registral", "OMISO", "DIRECTA", "Detecta presencia registral sin declaracion."),
    "R3": ReglaFiscal("R3", "Brecha exogena DIAN", "INEXACTO", "DIRECTA", "Compara ingresos DIAN contra bases ICA."),
    "R4": ReglaFiscal("R4", "Brecha facturacion electronica", "OMISO_INEXACTO", "DIRECTA", "Compara facturacion local contra declaracion."),
    "R5": ReglaFiscal("R5", "Contratista estatal no declarante", "OMISO_INEXACTO", "DIRECTA", "Cruza contratos SECOP contra ICA."),
    "R6": ReglaFiscal("R6", "Declarante en cero persistente", "INEXACTO", "INDICIARIA", "Identifica ceros con senales de actividad."),
    "R7": ReglaFiscal("R7", "CIIU conveniente", "INEXACTO", "MEDIA", "Detecta actividad declarada con menor tarifa."),
    "R8": ReglaFiscal("R8", "Atipico sectorial", "INEXACTO", "INDICIARIA", "Detecta comportamiento atipico contra pares."),
    "R9": ReglaFiscal("R9", "Territorialidad", "INEXACTO", "MEDIA", "Identifica ingresos fugados a otro municipio."),
    "R10": ReglaFiscal("R10", "Caida abrupta de base", "INEXACTO", "INDICIARIA", "Detecta caidas interanuales atipicas."),
}


def obtener_regla(codigo: str) -> ReglaFiscal:
    try:
        return RULES[codigo]
    except KeyError as exc:
        raise ValueError(f"Regla fiscal no soportada: {codigo}") from exc

