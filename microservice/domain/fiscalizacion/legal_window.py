from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class VentanaLegal:
    periodo: str
    fecha_vencimiento_declaracion: date
    limite_firmeza: date
    limite_aforo: date

    def limite_para(self, es_omiso: bool) -> date:
        return self.limite_aforo if es_omiso else self.limite_firmeza

    def es_accionable(self, hoy: date, es_omiso: bool) -> bool:
        return hoy <= self.limite_para(es_omiso)

    def dias_restantes(self, hoy: date, es_omiso: bool) -> int:
        return (self.limite_para(es_omiso) - hoy).days


def calcular_ventana_legal(periodo: str) -> VentanaLegal:
    year = _extraer_anio(periodo)
    vencimiento = date(year + 1, 4, 30)
    return VentanaLegal(
        periodo=periodo,
        fecha_vencimiento_declaracion=vencimiento,
        limite_firmeza=date(vencimiento.year + 3, vencimiento.month, vencimiento.day),
        limite_aforo=date(vencimiento.year + 5, vencimiento.month, vencimiento.day),
    )


def es_omiso(tipo_hallazgo: str) -> bool:
    return "OMISO" in tipo_hallazgo.upper()


def _extraer_anio(periodo: str) -> int:
    digits = "".join(ch for ch in str(periodo) if ch.isdigit())
    if len(digits) < 4:
        raise ValueError(f"Periodo invalido para ventana legal: {periodo}")
    return int(digits[:4])

