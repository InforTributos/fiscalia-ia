import uuid
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from application.use_cases.analizar_comportamiento import AnalizarComportamientoUseCase
from application.use_cases.analizar_grafo_riesgo import AnalizarGrafoRiesgoUseCase
from application.use_cases.aplicar_reglas_fiscales import AplicarReglasFiscalesUseCase
from application.use_cases.construir_perfil_fiscal import (
    construir_perfil_fiscal_desde_datos_originales,
)
from application.use_cases.generar_expediente_fiscal import GenerarExpedienteFiscalUseCase
from application.use_cases.gestionar_hallazgos import GestionarHallazgosUseCase
from application.use_cases.revisar_hallazgo_agente import (
    RevisarHallazgoAgenteUseCase,
    _compactar_hallazgo,
)
from domain.errors import (
    HallazgoNoEncontradoError,
    NITNoEncontradoError,
    ProcesoNoEncontradoError,
    SolicitudInvalidaError,
)


# ── Fixtures compartidos ──


@pytest.fixture
def mock_behavioral_repo():
    repo = AsyncMock()
    repo.obtener_contribuyente = AsyncMock()
    repo.obtener_pares = AsyncMock()
    return repo


@pytest.fixture
def mock_proceso_repo():
    repo = AsyncMock()
    repo.obtener_proceso = AsyncMock()
    repo.listar_proceso_detalle = AsyncMock()
    return repo


@pytest.fixture
def mock_graph_repo():
    repo = AsyncMock()
    repo.obtener_contribuyente = AsyncMock()
    repo.obtener_relacionados = AsyncMock()
    return repo


def _mock_cm(**kwargs):
    m = MagicMock()
    for k, v in kwargs.items():
        setattr(m, k, v)
    return m


# ════════════════════════════════════════════════════════════════
# 1. AnalizarComportamientoUseCase
# ════════════════════════════════════════════════════════════════


class TestAnalizarComportamientoUseCase:

    @patch("application.use_cases.analizar_comportamiento.build_contributor_metrics")
    @patch("application.use_cases.analizar_comportamiento.build_benchmark")
    @patch("application.use_cases.analizar_comportamiento.calcular_score_comportamental")
    async def test_analizar_nit_happy(
        self,
        mock_score,
        mock_benchmark,
        mock_metrics,
        mock_behavioral_repo,
        mock_proceso_repo,
    ):
        mock_behavioral_repo.obtener_contribuyente.return_value = {
            "nit": "123",
            "ciiu": "4711",
        }
        mock_behavioral_repo.obtener_pares.return_value = [
            {"nit": "456", "ciiu": "4711"},
            {"nit": "789", "ciiu": "4711"},
        ]
        mock_metrics.side_effect = [
            _mock_cm(nit="123", ciiu="4711", regimen="COMUN"),
            _mock_cm(nit="456", ciiu="4711", regimen="COMUN"),
            _mock_cm(nit="789", ciiu="4711", regimen="COMUN"),
        ]
        mock_benchmark.return_value = _mock_cm(total_pares=2)
        mock_score.return_value = {"score_comportamental": 75.0}

        uc = AnalizarComportamientoUseCase(
            behavioral_repo=mock_behavioral_repo,
            proceso_repo=mock_proceso_repo,
        )
        result = await uc.analizar_nit(nit="123", periodo="2024")
        assert result["score_comportamental"] == 75.0
        mock_behavioral_repo.obtener_contribuyente.assert_awaited_once_with("123", "2024")
        mock_behavioral_repo.obtener_pares.assert_awaited_once()

    @patch("application.use_cases.analizar_comportamiento.build_contributor_metrics")
    @patch("application.use_cases.analizar_comportamiento.build_benchmark")
    @patch("application.use_cases.analizar_comportamiento.calcular_score_comportamental")
    async def test_analizar_nit_con_ciiu_regimen(
        self,
        mock_score,
        mock_benchmark,
        mock_metrics,
        mock_behavioral_repo,
        mock_proceso_repo,
    ):
        mock_behavioral_repo.obtener_contribuyente.return_value = {
            "nit": "123",
            "ciiu": "4711",
            "regimen": "PREFERENCIAL",
        }
        mock_behavioral_repo.obtener_pares.return_value = []
        mock_metrics.return_value = _mock_cm(nit="123", ciiu="8520", regimen="COMUN")
        mock_benchmark.return_value = _mock_cm(total_pares=0)
        mock_score.return_value = {"score_comportamental": 50.0}

        uc = AnalizarComportamientoUseCase(
            behavioral_repo=mock_behavioral_repo,
            proceso_repo=mock_proceso_repo,
        )
        result = await uc.analizar_nit(
            nit="123", periodo="2024", ciiu="8520", regimen="COMUN",
        )
        assert result["score_comportamental"] == 50.0
        mock_behavioral_repo.obtener_pares.assert_awaited_once_with("2024", "8520", "COMUN")

    async def test_analizar_nit_no_encontrado(self, mock_behavioral_repo, mock_proceso_repo):
        mock_behavioral_repo.obtener_contribuyente.return_value = None
        uc = AnalizarComportamientoUseCase(
            behavioral_repo=mock_behavioral_repo,
            proceso_repo=mock_proceso_repo,
        )
        with pytest.raises(NITNoEncontradoError):
            await uc.analizar_nit(nit="999", periodo="2024")

    @patch("application.use_cases.analizar_comportamiento.build_contributor_metrics")
    @patch("application.use_cases.analizar_comportamiento.build_benchmark")
    @patch("application.use_cases.analizar_comportamiento.calcular_score_comportamental")
    async def test_analizar_nit_min_pares(
        self,
        mock_score,
        mock_benchmark,
        mock_metrics,
        mock_behavioral_repo,
        mock_proceso_repo,
    ):
        mock_behavioral_repo.obtener_contribuyente.return_value = {"nit": "123"}
        mock_behavioral_repo.obtener_pares.return_value = []
        mock_metrics.return_value = _mock_cm(nit="123", ciiu="4711", regimen=None)
        mock_benchmark.return_value = _mock_cm(total_pares=0)
        mock_score.return_value = {"score_comportamental": 30.0}

        uc = AnalizarComportamientoUseCase(
            behavioral_repo=mock_behavioral_repo,
            proceso_repo=mock_proceso_repo,
        )
        result = await uc.analizar_nit(nit="123", periodo="2024", min_pares=5)
        assert result["score_comportamental"] == 30.0
        mock_score.assert_called_once()
        assert mock_score.call_args[1]["min_pares"] == 5

    async def test_ranking_proceso_happy(self, mock_behavioral_repo, mock_proceso_repo):
        pid = uuid.uuid4()
        mock_proceso_repo.obtener_proceso.return_value = {
            "id": pid,
            "criteria": {"periodo": "2024"},
        }
        mock_proceso_repo.listar_proceso_detalle.return_value = (3, [
            {"nit": "111"},
            {"nit": "222"},
            {"nit": "333"},
        ])

        uc = AnalizarComportamientoUseCase(
            behavioral_repo=mock_behavioral_repo,
            proceso_repo=mock_proceso_repo,
        )
        uc.analizar_nit = AsyncMock(side_effect=[
            {"score_comportamental": 85.0},
            {"score_comportamental": 45.0},
            {"score_comportamental": 90.0},
        ])
        result = await uc.ranking_proceso(pid, limite=2, min_score=50)
        assert result["total_evaluados"] == 3
        assert result["total_rankeados"] == 2
        assert len(result["resultados"]) == 2
        assert result["resultados"][0]["score_comportamental"] == 90.0
        assert result["resultados"][1]["score_comportamental"] == 85.0
        assert result["errores"] == []

    async def test_ranking_proceso_no_encontrado(self, mock_behavioral_repo, mock_proceso_repo):
        mock_proceso_repo.obtener_proceso.return_value = None
        uc = AnalizarComportamientoUseCase(
            behavioral_repo=mock_behavioral_repo,
            proceso_repo=mock_proceso_repo,
        )
        with pytest.raises(ProcesoNoEncontradoError):
            await uc.ranking_proceso(uuid.uuid4())

    async def test_ranking_proceso_con_errores(self, mock_behavioral_repo, mock_proceso_repo):
        pid = uuid.uuid4()
        mock_proceso_repo.obtener_proceso.return_value = {"criteria": {"periodo": "2024"}}
        mock_proceso_repo.listar_proceso_detalle.return_value = (2, [
            {"nit": "111"},
            {"nit": "222"},
        ])

        uc = AnalizarComportamientoUseCase(
            behavioral_repo=mock_behavioral_repo,
            proceso_repo=mock_proceso_repo,
        )
        uc.analizar_nit = AsyncMock(side_effect=[
            {"score_comportamental": 80.0},
            Exception("MCP timeout"),
        ])
        result = await uc.ranking_proceso(pid, limite=10, min_score=0)
        assert result["total_evaluados"] == 2
        assert result["total_rankeados"] == 1
        assert len(result["errores"]) == 1
        assert result["errores"][0]["nit"] == "222"
        assert "MCP timeout" in result["errores"][0]["mensaje"]

    async def test_ranking_proceso_periodo_override(self, mock_behavioral_repo, mock_proceso_repo):
        pid = uuid.uuid4()
        mock_proceso_repo.obtener_proceso.return_value = {
            "criteria": {"periodo": "2023"},
        }
        mock_proceso_repo.listar_proceso_detalle.return_value = (1, [{"nit": "111"}])

        uc = AnalizarComportamientoUseCase(
            behavioral_repo=mock_behavioral_repo,
            proceso_repo=mock_proceso_repo,
        )
        uc.analizar_nit = AsyncMock(return_value={"score_comportamental": 70.0})
        result = await uc.ranking_proceso(pid, periodo="2025")
        assert result["periodo"] == "2025"

    async def test_ranking_proceso_sin_criteria(self, mock_behavioral_repo, mock_proceso_repo):
        pid = uuid.uuid4()
        mock_proceso_repo.obtener_proceso.return_value = {"id": pid}
        mock_proceso_repo.listar_proceso_detalle.return_value = (0, [])

        uc = AnalizarComportamientoUseCase(
            behavioral_repo=mock_behavioral_repo,
            proceso_repo=mock_proceso_repo,
        )
        result = await uc.ranking_proceso(pid)
        assert result["periodo"] == "2024"


# ════════════════════════════════════════════════════════════════
# 2. AnalizarGrafoRiesgoUseCase
# ════════════════════════════════════════════════════════════════


class TestAnalizarGrafoRiesgoUseCase:

    @patch("application.use_cases.analizar_grafo_riesgo.build_taxpayer_graph")
    @patch("application.use_cases.analizar_grafo_riesgo.graph_to_dict")
    @patch("application.use_cases.analizar_grafo_riesgo.calcular_riesgo_red")
    async def test_analizar_nit_con_comportamiento(
        self,
        mock_riesgo,
        mock_graph_dict,
        mock_build_graph,
        mock_graph_repo,
    ):
        mock_graph_repo.obtener_contribuyente.return_value = {"nit": "123"}
        mock_graph_repo.obtener_relacionados.return_value = []
        mock_build_graph.return_value = _mock_cm(nit="123", edges=[])
        mock_graph_dict.return_value = {"nit": "123", "nodes": [], "edges": []}
        mock_riesgo.return_value = {"score_red": 80.0, "bonus_red": 5}

        mock_comp_uc = MagicMock()
        mock_comp_uc.analizar_nit = AsyncMock(return_value={
            "score_comportamental": 75.0,
        })

        uc = AnalizarGrafoRiesgoUseCase(
            graph_repo=mock_graph_repo,
            comportamiento_use_case=mock_comp_uc,
        )
        result = await uc.analizar_nit(nit="123", periodo="2024")
        assert result["periodo"] == "2024"
        assert result["resumen_red"]["score_red"] == 80.0
        assert result["analisis_comportamental"]["score_comportamental"] == 75.0
        mock_comp_uc.analizar_nit.assert_awaited_once_with(
            nit="123", periodo="2024", min_pares=10,
        )

    @patch("application.use_cases.analizar_grafo_riesgo.build_taxpayer_graph")
    @patch("application.use_cases.analizar_grafo_riesgo.graph_to_dict")
    @patch("application.use_cases.analizar_grafo_riesgo.calcular_riesgo_red")
    async def test_analizar_nit_sin_comportamiento(
        self,
        mock_riesgo,
        mock_graph_dict,
        mock_build_graph,
        mock_graph_repo,
    ):
        mock_graph_repo.obtener_contribuyente.return_value = {"nit": "123"}
        mock_graph_repo.obtener_relacionados.return_value = []
        mock_build_graph.return_value = _mock_cm(nit="123", edges=[])
        mock_graph_dict.return_value = {"nit": "123", "nodes": [], "edges": []}
        mock_riesgo.return_value = {"score_red": 50.0, "bonus_red": 0}

        uc = AnalizarGrafoRiesgoUseCase(
            graph_repo=mock_graph_repo,
        )
        uc.comportamiento_use_case.analizar_nit = AsyncMock()
        result = await uc.analizar_nit(
            nit="123", periodo="2024", incluir_comportamiento=False,
        )
        assert result["analisis_comportamental"] is None
        uc.comportamiento_use_case.analizar_nit.assert_not_awaited()

    async def test_analizar_nit_no_encontrado(self, mock_graph_repo):
        mock_graph_repo.obtener_contribuyente.return_value = None
        uc = AnalizarGrafoRiesgoUseCase(graph_repo=mock_graph_repo)
        with pytest.raises(NITNoEncontradoError):
            await uc.analizar_nit(nit="999", periodo="2024")

    @patch("application.use_cases.analizar_grafo_riesgo.build_taxpayer_graph")
    @patch("application.use_cases.analizar_grafo_riesgo.graph_to_dict")
    @patch("application.use_cases.analizar_grafo_riesgo.calcular_riesgo_red")
    async def test_analizar_nit_sin_comportamiento_y_sin_score(
        self,
        mock_riesgo,
        mock_graph_dict,
        mock_build_graph,
        mock_graph_repo,
    ):
        mock_graph_repo.obtener_contribuyente.return_value = {"nit": "123"}
        mock_graph_repo.obtener_relacionados.return_value = []
        mock_build_graph.return_value = _mock_cm(nit="123", edges=[])
        mock_graph_dict.return_value = {"nit": "123"}
        mock_riesgo.return_value = {"score_red": 0.0, "bonus_red": 0}

        uc = AnalizarGrafoRiesgoUseCase(graph_repo=mock_graph_repo)
        uc.comportamiento_use_case.analizar_nit = AsyncMock()
        result = await uc.analizar_nit(
            nit="123", periodo="2024", incluir_comportamiento=False,
        )
        assert result["analisis_comportamental"] is None
        assert result["resumen_red"]["score_red"] == 0.0


# ════════════════════════════════════════════════════════════════
# 3. AplicarReglasFiscalesUseCase
# ════════════════════════════════════════════════════════════════


class TestAplicarReglasFiscalesUseCase:

    @patch("application.use_cases.aplicar_reglas_fiscales.evaluar_reglas")
    async def test_evaluar(self, mock_evaluar):
        mock_evaluar.return_value = [
            {"regla": "R1", "nit": "123", "periodo": "2024", "tipo_hallazgo": "OMISO"},
        ]
        uc = AplicarReglasFiscalesUseCase()
        result = await uc.evaluar({"nit": "123"})
        assert len(result) == 1
        assert result[0]["regla"] == "R1"

    @patch("application.use_cases.aplicar_reglas_fiscales.evaluar_reglas")
    async def test_evaluar_con_reglas_especificas(self, mock_evaluar):
        mock_evaluar.return_value = [{"regla": "R3", "nit": "123"}]
        uc = AplicarReglasFiscalesUseCase()
        result = await uc.evaluar({"nit": "123"}, reglas=["R3", "R5"])
        mock_evaluar.assert_called_once_with({"nit": "123"}, reglas=["R3", "R5"])

    @patch("application.use_cases.aplicar_reglas_fiscales.evaluar_reglas")
    async def test_evaluar_vacio(self, mock_evaluar):
        mock_evaluar.return_value = []
        uc = AplicarReglasFiscalesUseCase()
        result = await uc.evaluar({"nit": "123"})
        assert result == []

    @patch("application.use_cases.aplicar_reglas_fiscales.evaluar_reglas")
    @patch("application.use_cases.aplicar_reglas_fiscales.GestionarHallazgosUseCase.crear_hallazgo", new_callable=AsyncMock)
    async def test_ejecutar(self, mock_crear, mock_evaluar):
        mock_evaluar.return_value = [
            {"nit": "123", "regla": "R1", "periodo": "2024", "tipo_hallazgo": "OMISO"},
            {"nit": "123", "regla": "R2", "periodo": "2024", "tipo_hallazgo": "INEXACTO"},
        ]
        mock_crear.side_effect = [
            {"id": 1},
            {"id": 2},
        ]
        uc = AplicarReglasFiscalesUseCase()
        result = await uc.ejecutar({"nit": "123", "periodo": "2024"})
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2

    @patch("application.use_cases.aplicar_reglas_fiscales.evaluar_reglas")
    @patch("application.use_cases.aplicar_reglas_fiscales.GestionarHallazgosUseCase.crear_hallazgo", new_callable=AsyncMock)
    async def test_ejecutar_vacio(self, mock_crear, mock_evaluar):
        mock_evaluar.return_value = []
        uc = AplicarReglasFiscalesUseCase()
        result = await uc.ejecutar({"nit": "123"})
        assert result == []
        mock_crear.assert_not_awaited()


# ════════════════════════════════════════════════════════════════
# 4. construir_perfil_fiscal_desde_datos_originales
# ════════════════════════════════════════════════════════════════


class TestConstruirPerfilFiscal:

    def test_perfil_completo(self):
        datos = {
            "nit": "9003189639",
            "razon_social": "EMPRESA TEST SAS",
            "ciiu": "4711",
            "regimen": "COMUN",
            "rues_estado": "ACTIVO",
            "declaraciones_ica": [
                {"periodo": "2024", "base_gravable": 100000000},
                {"periodo": "2023", "base_gravable": 80000000},
            ],
            "retenciones_ica": [
                {"valor_retenido": 5000000},
            ],
            "exogena_dian": [
                {"periodo": "2024", "ingresos": 150000000},
                {"periodo": "2024", "valor": 20000000},
            ],
            "facturacion_electronica": [
                {"valor": 120000000, "local": True},
            ],
            "contratos_publicos": [
                {"valor": 30000000},
            ],
        }
        perfil = construir_perfil_fiscal_desde_datos_originales(datos, periodo="2024")
        assert perfil["nit"] == "9003189639"
        assert perfil["razon_social"] == "EMPRESA TEST SAS"
        assert perfil["ciiu"] == "4711"
        assert perfil["regimen"] == "COMUN"
        assert perfil["presencia_registral"] is True
        assert perfil["vinculo_local"] is True
        assert len(perfil["declaraciones_ica"]) == 2
        assert len(perfil["exogena_dian"]) == 2
        assert len(perfil["senales_actividad"]) == 1
        assert perfil["senales_actividad"][0]["valor"] == 170000000
        assert len(perfil["historico_bases"]) == 2
        assert perfil["historico_bases"][0]["base_gravable"] == 100000000
        assert perfil["metadata"]["origen"] == "CONTRATO_ORIGINAL"
        assert perfil["metadata"]["rues_estado"] == "ACTIVO"

    def test_perfil_vacio(self):
        perfil = construir_perfil_fiscal_desde_datos_originales({}, periodo="2024")
        assert perfil["nit"] == ""
        assert perfil["declaraciones_ica"] == []
        assert perfil["exogena_dian"] == []
        assert perfil["senales_actividad"] == []
        assert perfil["historico_bases"] == []
        assert perfil["presencia_registral"] is False
        assert perfil["vinculo_local"] is False

    def test_perfil_rues_inactivo(self):
        perfil = construir_perfil_fiscal_desde_datos_originales(
            {"rues_estado": "INACTIVO"}, periodo="2024",
        )
        assert perfil["presencia_registral"] is False
        assert perfil["vinculo_local"] is False

    def test_perfil_rues_cancelado(self):
        perfil = construir_perfil_fiscal_desde_datos_originales(
            {"rues_estado": "CANCELADO"}, periodo="2024",
        )
        assert perfil["presencia_registral"] is False

    def test_perfil_sin_declaraciones(self):
        datos = {
            "exogena_dian": [{"ingresos": 50000000}],
        }
        perfil = construir_perfil_fiscal_desde_datos_originales(datos, periodo="2024")
        assert perfil["declaraciones_ica"] == []
        assert len(perfil["senales_actividad"]) == 1
        assert perfil["historico_bases"] == []

    def test_perfil_declaraciones_sin_base_gravable(self):
        datos = {
            "declaraciones_ica": [
                {"periodo": "2024"},
                {"periodo": "2023", "base_gravable": None},
            ],
        }
        perfil = construir_perfil_fiscal_desde_datos_originales(datos, periodo="2024")
        assert perfil["historico_bases"][0]["base_gravable"] == 0.0
        assert perfil["historico_bases"][1]["base_gravable"] == 0.0

    def test_perfil_con_reglas(self):
        perfil = construir_perfil_fiscal_desde_datos_originales(
            {}, periodo="2024", reglas=["R1", "R2"],
        )
        assert perfil["reglas"] == ["R1", "R2"]

    def test_perfil_enteros_en_campos_numericos(self):
        datos = {
            "declaraciones_ica": [
                {"periodo": "2024", "base_gravable": 50000000},
            ],
            "exogena_dian": [
                {"ingresos": 100000000},
            ],
        }
        perfil = construir_perfil_fiscal_desde_datos_originales(datos, periodo="2024")
        assert isinstance(perfil["historico_bases"][0]["base_gravable"], float)
        assert isinstance(perfil["senales_actividad"][0]["valor"], float)


# ════════════════════════════════════════════════════════════════
# 5. GenerarExpedienteFiscalUseCase
# ════════════════════════════════════════════════════════════════


class TestGenerarExpedienteFiscalUseCase:

    @patch("application.use_cases.generar_expediente_fiscal.construir_expediente_fiscal")
    @patch("application.use_cases.generar_expediente_fiscal.expediente_to_markdown")
    async def test_generar(self, mock_md, mock_exp, mock_graph_repo):
        grafo_result = {
            "nit": "123",
            "periodo": "2024",
        }
        mock_expediente_uc = MagicMock()
        mock_expediente_uc.analizar_nit = AsyncMock(return_value=grafo_result)

        mock_exp.return_value = {
            "nit": "123",
            "periodo": "2024",
            "score": {"score_fiscal_unificado": 85},
        }
        mock_md.return_value = "# Markdown"

        uc = GenerarExpedienteFiscalUseCase(grafo_use_case=mock_expediente_uc)
        result = await uc.generar(nit="123", periodo="2024")
        assert result["nit"] == "123"
        assert result["periodo"] == "2024"
        assert result["markdown"] == "# Markdown"
        mock_expediente_uc.analizar_nit.assert_awaited_once_with(
            nit="123", periodo="2024", min_pares=10, incluir_comportamiento=True,
        )
        mock_exp.assert_called_once_with(grafo_result)
        mock_md.assert_called_once_with(mock_exp.return_value)

    @patch("application.use_cases.generar_expediente_fiscal.construir_expediente_fiscal")
    @patch("application.use_cases.generar_expediente_fiscal.expediente_to_markdown")
    async def test_generar_sin_analisis(
        self,
        mock_md,
        mock_exp,
        mock_graph_repo,
    ):
        mock_expediente_uc = MagicMock()
        mock_expediente_uc.analizar_nit = AsyncMock(return_value={})

        mock_exp.return_value = {"nit": "", "periodo": "", "score": {}}
        mock_md.return_value = "# Markdown"

        uc = GenerarExpedienteFiscalUseCase(grafo_use_case=mock_expediente_uc)
        result = await uc.generar(nit="999", periodo="2024")

        assert result["markdown"] == "# Markdown"


# ════════════════════════════════════════════════════════════════
# 6. GestionarHallazgosUseCase
# ════════════════════════════════════════════════════════════════


class TestGestionarHallazgosUseCase:

    # ── crear_hallazgo ──

    @patch(
        "application.use_cases.gestionar_hallazgos.hallazgos_queries.crear_hallazgo",
        new_callable=AsyncMock,
    )
    async def test_crear_hallazgo_minimo(self, mock_create):
        mock_create.return_value = {"id": 1, "nit": "123", "regla": "R8"}
        uc = GestionarHallazgosUseCase()
        result = await uc.crear_hallazgo({
            "nit": "123",
            "regla": "R8",
            "periodo": "2024",
        })
        assert result["id"] == 1
        mock_create.assert_awaited_once()
        data = mock_create.call_args[0][0]
        assert data["nit"] == "123"
        assert data["regla"] == "R8"
        assert data["tipo_hallazgo"] == "INEXACTO"
        assert data["fuerza_probatoria"] == "INDICIARIA"
        assert isinstance(data["score"], (int, float))
        assert "score_componentes" in data
        assert data["ventana_limite"] is not None
        assert data["accionable"] is True
        assert data["resumen"] is not None

    @patch(
        "application.use_cases.gestionar_hallazgos.hallazgos_queries.crear_hallazgo",
        new_callable=AsyncMock,
    )
    async def test_crear_hallazgo_completo(self, mock_create):
        mock_create.return_value = {"id": 42}
        uc = GestionarHallazgosUseCase()
        result = await uc.crear_hallazgo({
            "nit": "9003189639",
            "regla": "R3",
            "periodo": "2024",
            "tipo_hallazgo": "INEXACTO",
            "fuerza_probatoria": "DIRECTA",
            "brecha_valor": 5000000.0,
            "impuesto_estimado": 15000000.0,
            "reincidencia": 2,
            "corroboracion": 3,
            "resumen": "Discrepancia en ingresos",
            "metadata": {"fuente": "DIAN"},
            "evidencias": [
                {"fuente": "DIAN", "referencia_registro": "EXT-001"},
            ],
        })
        assert result["id"] == 42
        data, evidencias = mock_create.call_args[0]
        assert data["nit"] == "9003189639"
        assert data["regla"] == "R3"
        assert data["tipo_hallazgo"] == "INEXACTO"
        assert data["fuerza_probatoria"] == "DIRECTA"
        assert data["brecha_valor"] == 5000000.0
        assert data["impuesto_estimado"] == 15000000.0
        assert data["score"] > 0
        assert len(evidencias) == 1

    async def test_crear_hallazgo_regla_invalida(self):
        uc = GestionarHallazgosUseCase()
        with pytest.raises(SolicitudInvalidaError) as exc:
            await uc.crear_hallazgo({
                "nit": "123",
                "regla": "R99",
                "periodo": "2024",
            })
        assert "R99" in str(exc.value)

    async def test_crear_hallazgo_regla_faltante(self):
        uc = GestionarHallazgosUseCase()
        with pytest.raises(KeyError):
            await uc.crear_hallazgo({
                "nit": "123",
                "periodo": "2024",
            })

    @patch(
        "application.use_cases.gestionar_hallazgos.hallazgos_queries.crear_hallazgo",
        new_callable=AsyncMock,
    )
    async def test_crear_hallazgo_omiso(self, mock_create):
        mock_create.return_value = {"id": 10}
        uc = GestionarHallazgosUseCase()
        await uc.crear_hallazgo({
            "nit": "123",
            "regla": "R2",
            "periodo": "2024",
        })
        data = mock_create.call_args[0][0]
        assert data["tipo_hallazgo"] == "OMISO"
        assert data["estado"] == "DETECTADO"

    @patch(
        "application.use_cases.gestionar_hallazgos.hallazgos_queries.crear_hallazgo",
        new_callable=AsyncMock,
    )
    async def test_crear_hallazgo_no_accionable(self, mock_create):
        mock_create.return_value = {"id": 11}
        uc = GestionarHallazgosUseCase()
        await uc.crear_hallazgo({
            "nit": "123",
            "regla": "R8",
            "periodo": "2015",
        })
        data = mock_create.call_args[0][0]
        assert data["accionable"] is False
        assert data["estado"] == "NO_ACCIONABLE"

    # ── crear_desde_grafo ──

    @patch(
        "application.use_cases.gestionar_hallazgos.GenerarExpedienteFiscalUseCase.generar",
        new_callable=AsyncMock,
    )
    async def test_crear_desde_grafo(self, mock_generar):
        mock_generar.return_value = {
            "analisis_comportamental": {
                "metricas": {"ingresos_exogena": 100000, "base_gravable": 50000},
            },
            "grafo": {
                "resumen_red": {"bonus_red": 5},
            },
            "resumen_ejecutivo": "Contribuyente con anomalias",
            "score": {"score_fiscal_unificado": 85},
        }
        uc = GestionarHallazgosUseCase()
        uc.crear_hallazgo = AsyncMock(return_value={"id": 99})
        result = await uc.crear_desde_grafo(nit="123", periodo="2024")
        assert result["id"] == 99
        uc.crear_hallazgo.assert_awaited_once()
        payload = uc.crear_hallazgo.call_args[0][0]
        assert payload["nit"] == "123"
        assert payload["regla"] == "R8"
        assert payload["tipo_hallazgo"] == "INEXACTO_INDICIARIO"
        assert payload["brecha_valor"] == 50000
        assert payload["corroboracion"] == 2
        assert payload["metadata"]["origen"] == "GRAFO_RIESGO"

    @patch(
        "application.use_cases.gestionar_hallazgos.GenerarExpedienteFiscalUseCase.generar",
        new_callable=AsyncMock,
    )
    async def test_crear_desde_grafo_sin_bonus_red(self, mock_generar):
        mock_generar.return_value = {
            "analisis_comportamental": {},
            "grafo": {
                "resumen_red": {"bonus_red": 0},
            },
            "resumen_ejecutivo": "Sin anomalias",
            "score": {"score_fiscal_unificado": 30},
        }
        uc = GestionarHallazgosUseCase()
        uc.crear_hallazgo = AsyncMock(return_value={"id": 100})
        await uc.crear_desde_grafo(nit="456", periodo="2024")
        payload = uc.crear_hallazgo.call_args[0][0]
        assert payload["brecha_valor"] == 0
        assert payload["corroboracion"] == 1

    # ── obtener ──

    @patch(
        "application.use_cases.gestionar_hallazgos.hallazgos_queries.obtener_hallazgo",
        new_callable=AsyncMock,
    )
    async def test_obtener(self, mock_obtener):
        hid = uuid.uuid4()
        mock_obtener.return_value = {"id": hid, "nit": "123"}
        uc = GestionarHallazgosUseCase()
        result = await uc.obtener(hid)
        assert result["id"] == hid
        mock_obtener.assert_awaited_once_with(hid)

    @patch(
        "application.use_cases.gestionar_hallazgos.hallazgos_queries.obtener_hallazgo",
        new_callable=AsyncMock,
    )
    async def test_obtener_no_encontrado(self, mock_obtener):
        mock_obtener.return_value = None
        uc = GestionarHallazgosUseCase()
        with pytest.raises(HallazgoNoEncontradoError):
            await uc.obtener(uuid.uuid4())

    # ── listar ──

    @patch(
        "application.use_cases.gestionar_hallazgos.hallazgos_queries.listar_hallazgos",
        new_callable=AsyncMock,
    )
    async def test_listar(self, mock_listar):
        mock_listar.return_value = (2, [{"id": 1}, {"id": 2}])
        uc = GestionarHallazgosUseCase()
        total, rows = await uc.listar()
        assert total == 2
        assert len(rows) == 2

    @patch(
        "application.use_cases.gestionar_hallazgos.hallazgos_queries.listar_hallazgos",
        new_callable=AsyncMock,
    )
    async def test_listar_vacio(self, mock_listar):
        mock_listar.return_value = (0, [])
        uc = GestionarHallazgosUseCase()
        total, rows = await uc.listar()
        assert total == 0
        assert rows == []

    @patch(
        "application.use_cases.gestionar_hallazgos.hallazgos_queries.listar_hallazgos",
        new_callable=AsyncMock,
    )
    async def test_listar_con_filtros(self, mock_listar):
        uc = GestionarHallazgosUseCase()
        await uc.listar(estado="DETECTADO", nit="123")
        mock_listar.assert_awaited_once_with(estado="DETECTADO", nit="123")

    # ── revisar ──

    @patch(
        "application.use_cases.gestionar_hallazgos.hallazgos_queries.registrar_revision",
        new_callable=AsyncMock,
    )
    async def test_revisar(self, mock_revisar):
        hid = uuid.uuid4()
        mock_revisar.return_value = {"id": hid, "estado": "VALIDADO"}
        uc = GestionarHallazgosUseCase()
        result = await uc.revisar(hid, "FUNC-001", "VALIDAR", "motivo")
        assert result["id"] == hid
        mock_revisar.assert_awaited_once_with(hid, "FUNC-001", "VALIDAR", "motivo")

    @patch(
        "application.use_cases.gestionar_hallazgos.hallazgos_queries.registrar_revision",
        new_callable=AsyncMock,
    )
    async def test_revisar_no_encontrado(self, mock_revisar):
        mock_revisar.return_value = None
        uc = GestionarHallazgosUseCase()
        with pytest.raises(HallazgoNoEncontradoError):
            await uc.revisar(uuid.uuid4(), "FUNC-001", "DESCARTAR", "sin fundamento")


# ════════════════════════════════════════════════════════════════
# 7. RevisarHallazgoAgenteUseCase
# ════════════════════════════════════════════════════════════════


def _hallazgo_ejemplo() -> dict:
    return {
        "id": uuid.uuid4(),
        "nit": "9003189639",
        "regla": "R8",
        "periodo": "2024",
        "tipo_hallazgo": "INEXACTO",
        "fuerza_probatoria": "DIRECTA",
        "brecha_valor": 5000000.0,
        "impuesto_estimado": 15000000.0,
        "score": 85.0,
        "accionable": True,
        "estado": "DETECTADO",
        "resumen": "Discrepancia detectada",
        "evidencias": [
            {"fuente": "DIAN", "descripcion": "Registro exogena", "snapshot": "{}"},
            {"fuente": "MCP", "descripcion": "Dato fiscal", "snapshot": "{}"},
        ],
    }


class TestRevisarHallazgoAgenteUseCase:

    @patch(
        "application.use_cases.revisar_hallazgo_agente.GestionarHallazgosUseCase.obtener",
        new_callable=AsyncMock,
    )
    @patch(
        "application.use_cases.revisar_hallazgo_agente.LLMService",
    )
    @patch(
        "application.use_cases.revisar_hallazgo_agente.hallazgos_queries.registrar_revision_agente",
        new_callable=AsyncMock,
    )
    async def test_revisar_con_ia(
        self,
        mock_registrar,
        mock_llm_cls,
        mock_obtener,
    ):
        hallazgo = _hallazgo_ejemplo()
        mock_obtener.return_value = hallazgo

        mock_llm_instance = MagicMock()
        mock_llm_instance.analyze = AsyncMock(return_value={
            "comentario": "Riesgo medio",
            "riesgos": ["Falta documento"],
            "preguntas": ["Que originó?"],
            "modo_degradado": False,
            "tokens_entrada": 150,
            "tokens_salida": 50,
        })
        mock_llm_cls.return_value = mock_llm_instance

        mock_registrar.return_value = {"id": 100, "hallazgo_id": hallazgo["id"]}

        uc = RevisarHallazgoAgenteUseCase()
        result = await uc.revisar(hallazgo_id=hallazgo["id"], usar_ia=True)
        assert result["id"] == 100
        mock_registrar.assert_awaited_once()
        call_kwargs = mock_registrar.call_args[1]
        assert call_kwargs["hallazgo_id"] == hallazgo["id"]
        assert call_kwargs["agente"] == "revisor_hallazgos"
        assert call_kwargs["modo_degradado"] is False
        assert call_kwargs["tokens_entrada"] > 0
        assert call_kwargs["tokens_salida"] > 0

    @patch(
        "application.use_cases.revisar_hallazgo_agente.GestionarHallazgosUseCase.obtener",
        new_callable=AsyncMock,
    )
    @patch(
        "application.use_cases.revisar_hallazgo_agente.LLMService",
    )
    @patch(
        "application.use_cases.revisar_hallazgo_agente.hallazgos_queries.registrar_revision_agente",
        new_callable=AsyncMock,
    )
    async def test_revisar_sin_ia(
        self,
        mock_registrar,
        mock_llm_cls,
        mock_obtener,
    ):
        hallazgo = _hallazgo_ejemplo()
        mock_obtener.return_value = hallazgo

        mock_llm_instance = MagicMock()
        mock_llm_instance.analyze = AsyncMock()
        mock_llm_cls.return_value = mock_llm_instance

        mock_registrar.return_value = {"id": 200}

        uc = RevisarHallazgoAgenteUseCase()
        result = await uc.revisar(hallazgo_id=hallazgo["id"], usar_ia=False)
        assert result["id"] == 200
        mock_llm_instance.analyze.assert_not_awaited()
        kwargs = mock_registrar.call_args[1]
        assert kwargs["modo_degradado"] is False
        assert kwargs["tokens_entrada"] == 0
        assert kwargs["tokens_salida"] == 0

    @patch(
        "application.use_cases.revisar_hallazgo_agente.GestionarHallazgosUseCase.obtener",
        new_callable=AsyncMock,
    )
    @patch(
        "application.use_cases.revisar_hallazgo_agente.LLMService",
    )
    @patch(
        "application.use_cases.revisar_hallazgo_agente.hallazgos_queries.registrar_revision_agente",
        new_callable=AsyncMock,
    )
    async def test_revisar_con_ia_degradado(
        self,
        mock_registrar,
        mock_llm_cls,
        mock_obtener,
    ):
        hallazgo = _hallazgo_ejemplo()
        mock_obtener.return_value = hallazgo

        mock_llm_instance = MagicMock()
        mock_llm_instance.analyze = AsyncMock(return_value={
            "modo_degradado": True,
            "explicacion": "LLM no disponible",
            "tokens_entrada": 0,
            "tokens_salida": 0,
        })
        mock_llm_cls.return_value = mock_llm_instance

        mock_registrar.return_value = {"id": 300}

        uc = RevisarHallazgoAgenteUseCase()
        result = await uc.revisar(hallazgo_id=hallazgo["id"], usar_ia=True)
        assert result["id"] == 300
        kwargs = mock_registrar.call_args[1]
        assert kwargs["modo_degradado"] is True

    @patch(
        "application.use_cases.revisar_hallazgo_agente.GestionarHallazgosUseCase.obtener",
        new_callable=AsyncMock,
    )
    @patch(
        "application.use_cases.revisar_hallazgo_agente.hallazgos_queries.registrar_revision_agente",
        new_callable=AsyncMock,
    )
    async def test_revisar_contenido_resultado(
        self,
        mock_registrar,
        mock_obtener,
    ):
        hallazgo = _hallazgo_ejemplo()
        mock_obtener.return_value = hallazgo
        mock_registrar.return_value = {"id": 400}

        uc = RevisarHallazgoAgenteUseCase()
        result = await uc.revisar(hallazgo_id=hallazgo["id"], usar_ia=False)
        assert result["id"] == 400
        kwargs = mock_registrar.call_args[1]
        resultado = kwargs["resultado"]
        assert "agente" in resultado or "completitud" in resultado
        assert resultado.get("estado_revision") in ("COMPLETO", "REQUIERE_AJUSTES", "INCOMPLETO")


# ════════════════════════════════════════════════════════════════
# 8. _compactar_hallazgo (función módulo)
# ════════════════════════════════════════════════════════════════


class TestCompactarHallazgo:

    def test_compactar_completo(self):
        evidencias = [{"id": i, "fuente": "MCP"} for i in range(10)]
        hallazgo = {
            "nit": "123",
            "regla": "R1",
            "periodo": "2024",
            "tipo_hallazgo": "OMISO",
            "fuerza_probatoria": "DIRECTA",
            "brecha_valor": 1000000.0,
            "impuesto_estimado": 500000.0,
            "score": 90.0,
            "accionable": True,
            "estado": "DETECTADO",
            "resumen": "Test",
            "evidencias": evidencias,
        }
        comp = _compactar_hallazgo(hallazgo)
        assert comp["nit"] == "123"
        assert comp["regla"] == "R1"
        assert comp["score"] == 90.0
        assert comp["accionable"] is True
        assert len(comp["evidencias"]) == 5

    def test_compactar_minimo(self):
        comp = _compactar_hallazgo({})
        assert comp["nit"] is None
        assert comp["regla"] is None
        assert comp["evidencias"] == []

    def test_compactar_sin_evidencias(self):
        comp = _compactar_hallazgo({"nit": "123"})
        assert comp["nit"] == "123"
        assert comp["evidencias"] == []

    def test_compactar_pocas_evidencias(self):
        hallazgo = {"evidencias": [{"id": 1}]}
        comp = _compactar_hallazgo(hallazgo)
        assert len(comp["evidencias"]) == 1
