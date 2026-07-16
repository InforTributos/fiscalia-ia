from __future__ import annotations

import hashlib
from dataclasses import asdict

from domain.graph.models import GraphEdge, GraphNode, TaxpayerGraph

ATTRIBUTE_LABELS = {
    "representante": "Representante legal",
    "direccion": "Direccion",
    "telefono": "Telefono",
    "correo": "Correo",
}


def _stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha1(value.strip().lower().encode("utf-8")).hexdigest()[:12]
    return f"{prefix}:{digest}"


def _company_node(row: dict) -> GraphNode:
    contribuyente_nit = str(row.get("contribuyente_nit", ""))
    return GraphNode(
        id=f"empresa:{contribuyente_nit}",
        tipo="EMPRESA",
        label=str(row.get("razon_social") or contribuyente_nit),
        propiedades={
            "contribuyente_nit": contribuyente_nit,
            "ciiu": row.get("ciiu", ""),
            "regimen": row.get("regimen", row.get("tipo_regimen", "")),
        },
    )


def build_taxpayer_graph(
    contribuyente: dict,
    relacionados_por_atributo: dict[str, list[dict]],
    analisis_comportamental: dict | None = None,
) -> TaxpayerGraph:
    nodes_by_id: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []

    target = _company_node(contribuyente)
    nodes_by_id[target.id] = target

    ciiu = str(contribuyente.get("ciiu", ""))
    if ciiu:
        ciiu_node = GraphNode(
            id=f"ciiu:{ciiu}",
            tipo="ACTIVIDAD_CIIU",
            label=ciiu,
            propiedades={"ciiu": ciiu},
        )
        nodes_by_id[ciiu_node.id] = ciiu_node
        edges.append(GraphEdge(source=target.id, target=ciiu_node.id, tipo="TIENE_ACTIVIDAD", peso=0.4))

    for atributo, relacionados in relacionados_por_atributo.items():
        valor = str(contribuyente.get(atributo, "") or "")
        if not valor:
            continue
        attr_node = GraphNode(
            id=_stable_id(f"atributo:{atributo}", valor),
            tipo=f"ATRIBUTO_{atributo.upper()}",
            label=ATTRIBUTE_LABELS.get(atributo, atributo),
            propiedades={"valor": valor},
        )
        nodes_by_id[attr_node.id] = attr_node
        edges.append(GraphEdge(
            source=target.id,
            target=attr_node.id,
            tipo=f"USA_{atributo.upper()}",
            peso=_peso_atributo(atributo),
            evidencia={"valor": valor},
        ))

        for row in relacionados:
            if str(row.get("contribuyente_nit", "")) == str(contribuyente.get("contribuyente_nit", "")):
                continue
            related_node = _company_node(row)
            nodes_by_id[related_node.id] = related_node
            edges.append(GraphEdge(
                source=related_node.id,
                target=attr_node.id,
                tipo=f"USA_{atributo.upper()}",
                peso=_peso_atributo(atributo),
                evidencia={"valor": valor},
            ))
            edges.append(GraphEdge(
                source=target.id,
                target=related_node.id,
                tipo=f"COMPARTE_{atributo.upper()}",
                peso=_peso_atributo(atributo),
                evidencia={"valor": valor},
            ))

    if analisis_comportamental:
        for hallazgo in analisis_comportamental.get("hallazgos", []):
            tipo = str(hallazgo.get("tipo", "HALLAZGO"))
            hallazgo_node = GraphNode(
                id=_stable_id("hallazgo", tipo),
                tipo="HALLAZGO",
                label=tipo,
                propiedades={
                    "severidad": hallazgo.get("severidad", ""),
                    "descripcion": hallazgo.get("descripcion", ""),
                },
            )
            nodes_by_id[hallazgo_node.id] = hallazgo_node
            edges.append(GraphEdge(
                source=target.id,
                target=hallazgo_node.id,
                tipo="TIENE_HALLAZGO",
                peso=_peso_hallazgo(hallazgo.get("severidad")),
                evidencia=hallazgo.get("evidencia", {}),
            ))

    return TaxpayerGraph(
        contribuyente_nit=str(contribuyente.get("contribuyente_nit", "")),
        nodes=list(nodes_by_id.values()),
        edges=edges,
    )


def graph_to_dict(graph: TaxpayerGraph) -> dict:
    return {
        "contribuyente_nit": graph.contribuyente_nit,
        "nodes": [asdict(node) for node in graph.nodes],
        "edges": [asdict(edge) for edge in graph.edges],
    }


def _peso_atributo(atributo: str) -> float:
    return {
        "representante": 1.0,
        "direccion": 0.9,
        "telefono": 0.7,
        "correo": 0.7,
    }.get(atributo, 0.5)


def _peso_hallazgo(severidad: str | None) -> float:
    if severidad == "ALTA":
        return 1.0
    if severidad == "MEDIA":
        return 0.7
    return 0.4

