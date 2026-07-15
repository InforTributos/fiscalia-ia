from domain.graph.models import TaxpayerGraph
from domain.graph.network_score import calcular_riesgo_red
from domain.graph.taxpayer_graph import build_taxpayer_graph, graph_to_dict


def _make_graph():
    contrib = {"nit": "123", "razon_social": "Test", "ciiu": "1234", "regimen": "GENERAL"}
    relacionados = {
        "representante": [{"nit": "456", "razon_social": "Other", "ciiu": "1234"}],
        "direccion": [],
        "telefono": [],
        "correo": [],
    }
    return build_taxpayer_graph(contrib, relacionados)


def test_build_graph_has_nodes_and_edges():
    graph = _make_graph()
    assert len(graph.nodes) >= 2
    assert len(graph.edges) >= 1


def test_graph_to_dict():
    graph = _make_graph()
    d = graph_to_dict(graph)
    assert "nodes" in d
    assert "edges" in d
    assert isinstance(d["nodes"], list)


def test_network_score_with_connections():
    from domain.graph.models import GraphEdge, GraphNode
    graph = TaxpayerGraph(
        nit="123",
        nodes=[
            GraphNode(id="empresa:123", tipo="EMPRESA", label="Test"),
            GraphNode(id="empresa:456", tipo="EMPRESA", label="Other"),
        ],
        edges=[
            GraphEdge(source="empresa:123", target="empresa:456", tipo="COMPARTE_REPRESENTANTE", peso=1.0),
        ],
    )
    result = calcular_riesgo_red(graph, score_comportamental=50.0)
    assert "score_red" in result
    assert "bonus_red" in result
    assert result["empresas_conectadas"] >= 1


def test_network_score_without_connections():
    graph = TaxpayerGraph(nit="123", nodes=[], edges=[])
    result = calcular_riesgo_red(graph, score_comportamental=0.0)
    assert result["score_red"] == 0.0
    assert result["empresas_conectadas"] == 0
