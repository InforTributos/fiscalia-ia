"""Verify the R3 exógena fix: VLOR_BSE instead of VLOR_RTNCION, filter RD only.

SQL-level tests ensure the constants contain the right columns and filters.
Domain-level tests verify R3 fires correctly with VLOR_BSE-magnitude values.
"""
from domain.services.crosscheck_service import extraer_inconsistencias, calcular_srf


# ── SQL structure tests ──────────────────────────────────────────────

def test_exogena_periodo_sql_uses_vlor_bse():
    from infrastructure.mcp.behavioral import EXOGENA_PERIODO_SQL
    assert "vlor_bse" in EXOGENA_PERIODO_SQL.lower(), (
        "EXOGENA_PERIODO_SQL debe usar vlor_bse (base), no vlor_rtncion"
    )
    assert "vlor_rtncion" not in EXOGENA_PERIODO_SQL.lower(), (
        "EXOGENA_PERIODO_SQL no debe usar vlor_rtncion (retención)"
    )
    assert "cdgo_exgna_tpo_rgstro = 'RD'" in EXOGENA_PERIODO_SQL, (
        "EXOGENA_PERIODO_SQL debe filtrar solo retenciones recibidas (RD)"
    )


def test_historico_exogena_sql_uses_vlor_bse():
    from infrastructure.mcp.behavioral import HISTORICO_EXOGENA_SQL
    assert "vlor_bse" in HISTORICO_EXOGENA_SQL.lower()
    assert "vlor_rtncion" not in HISTORICO_EXOGENA_SQL.lower()
    assert "cdgo_exgna_tpo_rgstro = 'RD'" in HISTORICO_EXOGENA_SQL


def test_pares_metricas_sql_exo_subquery_uses_vlor_bse():
    from infrastructure.mcp.behavioral import PARES_METRICAS_SQL
    # Find the GI_G_EXOGENA_RETENCIONES subquery within PARES_METRICAS_SQL
    sql = PARES_METRICAS_SQL
    idx = sql.find("GI_G_EXOGENA_RETENCIONES")
    assert idx > 0, "PARES_METRICAS_SQL debe tener subquery de exógena"
    # Walk backwards to find the SELECT that starts this subquery
    sub_start = sql.rfind("SELECT", 0, idx)
    # Walk forward to find the closing parenthesis
    sub_end = sql.find(") exo_data", idx)
    assert sub_end > 0, "No se encontró el cierre de la subquery exo_data"
    subquery = sql[sub_start:sub_end]
    assert "vlor_bse" in subquery.lower(), (
        "Subquery de exógena en PARES_METRICAS_SQL debe usar vlor_bse"
    )
    assert "cdgo_exgna_tpo_rgstro = 'RD'" in subquery


def test_obtener_exogena_sql_uses_vlor_bse_for_ingresos():
    from infrastructure.mcp.pagination import OBTENER_EXOGENA_SQL
    assert "vlor_bse" in OBTENER_EXOGENA_SQL.lower(), (
        "OBTENER_EXOGENA_SQL.ingresos debe usar vlor_bse"
    )


def test_obtener_exogena_sql_uses_correct_case_codes():
    """Verify CASE codes match actual Oracle data: RD and RP."""
    from infrastructure.mcp.pagination import OBTENER_EXOGENA_SQL
    assert "'RD'" in OBTENER_EXOGENA_SQL, "retenciones recibidas debe usar 'RD'"
    assert "'RP'" in OBTENER_EXOGENA_SQL, "retenciones practicadas debe usar 'RP'"
    assert "'RECIBIDA'" not in OBTENER_EXOGENA_SQL, "código incorrecto 'RECIBIDA'"
    assert "'PRACTICADA'" not in OBTENER_EXOGENA_SQL, "código incorrecto 'PRACTICADA'"


def test_obtener_exogena_sql_retenciones_keep_vlor_rtncion():
    """retenciones_exogena_* columns should keep VLOR_RTNCION for comparison."""
    from infrastructure.mcp.pagination import OBTENER_EXOGENA_SQL
    assert "vlor_rtncion" in OBTENER_EXOGENA_SQL, (
        "retenciones_exogena_* deben usar vlor_rtncion (valor de retención)"
    )


# ── Domain-level R3 tests with realistic VLOR_BSE values ─────────────

def test_r3_subdeclaracion_detectada_con_vlor_bse():
    """R3 must detect SUBDECLARACION when VLOR_BSE (base) >> declared base."""
    datos = {
        "ciiu": "4711",
        "declaraciones_ica": [
            {"periodo": "2024-B1", "base_gravable": 50_000_000, "tarifa": 0.008, "impuesto": 400_000},
        ],
        # VLOR_BSE values: base reported by third parties = $120M
        "exogena_dian": [{"periodo": "2024", "ingresos": 120_000_000}],
        "rues_estado": "ACTIVO",
    }
    incs = extraer_inconsistencias(datos)
    subdecl = [i for i in incs if i["tipo"] == "SUBDECLARACION_EXOGENA"]
    assert len(subdecl) == 1
    assert subdecl[0]["declarado"] == 50_000_000
    assert subdecl[0]["exogena"] == 120_000_000
    assert subdecl[0]["severidad"] == "ALTA"
    assert subdecl[0]["variacion_pct"] > 15  # 140% difference


def test_r3_subdeclaracion_no_falsa_cuando_coinciden():
    """R3 should NOT fire when VLOR_BSE ≈ declared base."""
    datos = {
        "ciiu": "4711",
        "declaraciones_ica": [
            {"periodo": "2024-B1", "base_gravable": 100_000_000, "tarifa": 0.008, "impuesto": 800_000},
        ],
        "exogena_dian": [{"periodo": "2024", "ingresos": 100_000_000}],
        "rues_estado": "ACTIVO",
    }
    incs = extraer_inconsistencias(datos)
    subdecl = [i for i in incs if i["tipo"] == "SUBDECLARACION_EXOGENA"]
    assert len(subdecl) == 0, "No debe marcar si los valores coinciden"


def test_r3_subdeclaracion_ignora_dif_marginal():
    """R3 should NOT fire when difference is under 15% threshold."""
    datos = {
        "ciiu": "4711",
        "declaraciones_ica": [
            {"periodo": "2024-B1", "base_gravable": 100_000_000, "tarifa": 0.008, "impuesto": 800_000},
        ],
        "exogena_dian": [{"periodo": "2024", "ingresos": 110_000_000}],  # only 10% above
        "rues_estado": "ACTIVO",
    }
    incs = extraer_inconsistencias(datos)
    subdecl = [i for i in incs if i["tipo"] == "SUBDECLARACION_EXOGENA"]
    assert len(subdecl) == 0, "10% de diferencia está bajo el umbral del 15%"


def test_r3_sin_exogena_no_dispara():
    """R3 should not fire when there's no exógena data."""
    datos = {
        "ciiu": "4711",
        "declaraciones_ica": [
            {"periodo": "2024-B1", "base_gravable": 50_000_000, "tarifa": 0.008, "impuesto": 400_000},
        ],
        "exogena_dian": [],
        "rues_estado": "ACTIVO",
    }
    incs = extraer_inconsistencias(datos)
    subdecl = [i for i in incs if i["tipo"] == "SUBDECLARACION_EXOGENA"]
    assert len(subdecl) == 0


def test_r3_con_multiples_periodos_acumula():
    """R3 should accumulate across multiple declaration periods."""
    datos = {
        "ciiu": "4711",
        "declaraciones_ica": [
            {"periodo": "2024-B1", "base_gravable": 20_000_000, "tarifa": 0.008, "impuesto": 160_000},
            {"periodo": "2024-B2", "base_gravable": 30_000_000, "tarifa": 0.008, "impuesto": 240_000},
            # total declarado = 50M
        ],
        # VLOR_BSE from third party = $200M → 300% above
        "exogena_dian": [{"periodo": "2024", "ingresos": 200_000_000}],
        "rues_estado": "ACTIVO",
    }
    incs = extraer_inconsistencias(datos)
    subdecl = [i for i in incs if i["tipo"] == "SUBDECLARACION_EXOGENA"]
    assert len(subdecl) == 1
    assert subdecl[0]["declarado"] == 50_000_000
    assert subdecl[0]["exogena"] == 200_000_000
    assert subdecl[0]["variacion_pct"] > 100


def test_r3_srf_exogena_contribuye_al_score():
    """SRF score should include exógena component when difference > 15%."""
    datos = {
        "ciiu": "4711",
        "declaraciones_ica": [
            {"periodo": "2024-B1", "base_gravable": 50_000_000, "tarifa": 0.008, "impuesto": 400_000},
        ],
        "exogena_dian": [{"periodo": "2024", "ingresos": 200_000_000}],
        "rues_estado": "ACTIVO",
    }
    result = calcular_srf(datos)
    assert result["componentes"]["diferencia_exogena"]["valor"] > 0


def test_r3_srf_exogena_cero_sin_diferencia():
    """SRF exógena component should be 0 when values match."""
    datos = {
        "ciiu": "4711",
        "declaraciones_ica": [
            {"periodo": "2024-B1", "base_gravable": 100_000_000, "tarifa": 0.008, "impuesto": 800_000},
        ],
        "exogena_dian": [{"periodo": "2024", "ingresos": 100_000_000}],
        "rues_estado": "ACTIVO",
    }
    result = calcular_srf(datos)
    assert result["componentes"]["diferencia_exogena"]["valor"] == 0
