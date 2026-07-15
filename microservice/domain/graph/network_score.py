from __future__ import annotations

from collections import defaultdict

from domain.graph.models import TaxpayerGraph

BONUS_BY_EDGE = {
    "COMPARTE_REPRESENTANTE": 8,
    "COMPARTE_DIRECCION": 6,
    "COMPARTE_TELEFONO": 4,
    "COMPARTE_CORREO": 4,
}


def calcular_riesgo_red(graph: TaxpayerGraph, score_comportamental: float = 0.0) -> dict:
    target_id = f"empresa:{graph.nit}"
    bonus = 0.0
    motivos: list[str] = []
    empresas_conectadas: set[str] = set()
    atributos_por_empresa: dict[str, set[str]] = defaultdict(set)

    for edge in graph.edges:
        if edge.source != target_id or not edge.tipo.startswith("COMPARTE_"):
            continue
        empresas_conectadas.add(edge.target)
        atributo = edge.tipo.replace("COMPARTE_", "").lower()
        atributos_por_empresa[edge.target].add(atributo)
        bonus += BONUS_BY_EDGE.get(edge.tipo, 2)

    if empresas_conectadas:
        motivos.append(f"Conecta con {len(empresas_conectadas)} empresa(s) por atributos compartidos")

    multiatributo = [empresa for empresa, attrs in atributos_por_empresa.items() if len(attrs) >= 2]
    if multiatributo:
        bonus += min(len(multiatributo) * 5, 20)
        motivos.append(f"{len(multiatributo)} empresa(s) comparten dos o mas atributos con el contribuyente")

    if score_comportamental >= 70 and len(empresas_conectadas) >= 3:
        bonus += 10
        motivos.append("Riesgo comportamental alto combinado con varias conexiones de red")

    hallazgos_altos = sum(
        1
        for edge in graph.edges
        if edge.source == target_id and edge.tipo == "TIENE_HALLAZGO" and edge.peso >= 1.0
    )
    if hallazgos_altos:
        bonus += min(hallazgos_altos * 3, 12)
        motivos.append(f"{hallazgos_altos} hallazgo(s) de severidad alta enriquecen el grafo")

    bonus = min(bonus, 35)
    score_red = min(round(score_comportamental + bonus, 2), 100.0)
    return {
        "score_red": score_red,
        "score_comportamental": round(score_comportamental, 2),
        "bonus_red": round(bonus, 2),
        "nivel_red": _nivel(score_red),
        "empresas_conectadas": len(empresas_conectadas),
        "motivos": motivos or ["No se identificaron conexiones de red materiales con la informacion disponible"],
    }


def _nivel(score: float) -> str:
    if score >= 85:
        return "ALTO"
    if score >= 60:
        return "MEDIO"
    return "BAJO"

