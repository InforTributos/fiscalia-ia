from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GraphNode:
    id: str
    tipo: str
    label: str
    propiedades: dict = field(default_factory=dict)


@dataclass(frozen=True)
class GraphEdge:
    source: str
    target: str
    tipo: str
    peso: float = 1.0
    evidencia: dict = field(default_factory=dict)


@dataclass(frozen=True)
class TaxpayerGraph:
    contribuyente_nit: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]

