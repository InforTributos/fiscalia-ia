from domain.fiscal.dossier import construir_expediente_fiscal, expediente_to_markdown


def test_construir_expediente_minimo():
    grafo = {"contribuyente_nit": "9003189639", "periodo": "2024"}
    result = construir_expediente_fiscal(grafo)
    assert result["contribuyente_nit"] == "9003189639"
    assert result["periodo"] == "2024"
    assert result["score"]["prioridad"] == "BAJA"
    assert result["score"]["score_fiscal_unificado"] == 0.0
    assert result["grafo"]["total_nodos"] == 0
    assert result["grafo"]["total_relaciones"] == 0
    assert "generado_en" in result


def test_construir_expediente_con_analisis():
    grafo = {
        "contribuyente_nit": "9003189639",
        "periodo": "2024",
        "analisis_comportamental": {
            "score_comportamental": 100,
            "confianza": 1.0,
            "metricas": {"base_gravable": 500000000, "ratio_exogena_declarado": 0.85},
            "benchmark": {"mediana_base_gravable": 300000000},
            "hallazgos": [{"tipo": "R1", "fuerza_probatoria": "DIRECTA"}],
        },
        "resumen_red": {"score_red": 100, "empresas_conectadas": 5},
    }
    result = construir_expediente_fiscal(grafo)
    assert result["score"]["prioridad"] == "MEDIA"
    assert result["score"]["score_fiscal_unificado"] >= 50
    assert len(result["evidencia"]) > 0
    assert len(result["acciones_sugeridas"]) > 0


def test_construir_expediente_con_hallazgos():
    grafo = {
        "contribuyente_nit": "9003189639",
        "periodo": "2024",
        "analisis_comportamental": {
            "hallazgos": [
                {"tipo": "EXOGENA_CON_DECLARACION_CERO", "descripcion": "Exogena sin declaracion"},
                {"tipo": "R1", "descripcion": "Retenciones sin declaracion"},
            ],
        },
        "resumen_red": {},
    }
    result = construir_expediente_fiscal(grafo)
    assert result["score"]["prioridad"] == "BAJA"
    assert len(result["acciones_sugeridas"]) >= 1


def test_construir_expediente_con_hallazgo_exogena():
    grafo = {
        "contribuyente_nit": "9003189639",
        "periodo": "2024",
        "analisis_comportamental": {
            "hallazgos": [{"tipo": "EXOGENA_SIN_DECLARACION", "descripcion": "Diferencia exogena"}],
        },
        "resumen_red": {"empresas_conectadas": 2},
    }
    result = construir_expediente_fiscal(grafo)
    acciones = result["acciones_sugeridas"]
    assert any("Solicitar" in a for a in acciones)


def test_construir_expediente_sin_hallazgos():
    grafo = {
        "contribuyente_nit": "9003189639",
        "periodo": "2024",
        "analisis_comportamental": {"metricas": {}, "benchmark": {}},
        "resumen_red": {},
    }
    result = construir_expediente_fiscal(grafo)
    assert result["evidencia"] == ["No se encontro evidencia suficiente para priorizacion automatica"]
    assert result["acciones_sugeridas"] == ["Mantener en monitoreo y revisar si aparecen nuevos hallazgos"]


def test_expediente_to_markdown():
    expediente = {
        "contribuyente_nit": "9003189639",
        "periodo": "2024",
        "score": {"prioridad": "ALTA", "score_fiscal_unificado": 85.5},
        "resumen_ejecutivo": "Resumen de prueba",
        "evidencia": ["Evidencia 1", "Evidencia 2"],
        "acciones_sugeridas": ["Accion 1"],
    }
    md = expediente_to_markdown(expediente)
    assert "# Expediente Fiscal - NIT 9003189639" in md
    assert "Prioridad: ALTA" in md
    assert "Score fiscal unificado: 85.5" in md
    assert "- Evidencia 1" in md
    assert "- Accion 1" in md


def test_expediente_to_markdown_sin_evidencia():
    expediente = {
        "contribuyente_nit": "9003189639",
        "periodo": "2024",
        "score": {"prioridad": "BAJA", "score_fiscal_unificado": 10},
        "resumen_ejecutivo": "Sin novedades",
        "evidencia": [],
        "acciones_sugeridas": [],
    }
    md = expediente_to_markdown(expediente)
    assert "9003189639" in md
    assert "BAJA" in md


def test_resumen_con_evidencia_parcial():
    grafo = {
        "contribuyente_nit": "9003189639",
        "periodo": "2024",
        "analisis_comportamental": {
            "metricas": {"base_gravable": 100000000},
            "benchmark": {"mediana_base_gravable": 80000000},
        },
        "resumen_red": {},
    }
    result = construir_expediente_fiscal(grafo)
    assert "9003189639" in result["resumen_ejecutivo"]
    assert "Base gravable" in result["evidencia"][0]
