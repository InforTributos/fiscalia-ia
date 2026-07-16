from domain.errors import (
    ConfiguracionInvalidaError,
    CriteriosInvalidosError,
    EntidadNoEncontradoError,
    FiscalIAError,
    HallazgoNoEncontradoError,
    LLMAllProvidersFailedError,
    LLMInvalidJSONError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUnavailableError,
    LookupError,
    MCPConnectionError,
    MCPConnectionRefusedError,
    MCPPageError,
    MCPTimeoutError,
    NITNoEncontradoError,
    OracleQueryFailError,
    OracleTimeoutError,
    OrchestrationFailError,
    PGConnError,
    PGInsertFailError,
    ProcesoEnProcesoError,
    ProcesoNoEncontradoError,
    SolicitudInvalidaError,
    WorkerTimeoutError,
)


def test_fiscalia_error_base():
    err = FiscalIAError()
    assert err.codigo == "UNKNOWN_ERROR"
    assert err.status_code == 500
    assert err.mensaje == "Error interno del servidor"


def test_fiscalia_error_con_mensaje():
    err = FiscalIAError("Mensaje custom")
    assert err.mensaje == "Mensaje custom"


def test_nit_no_encontrado():
    err = NITNoEncontradoError("9003189639")
    assert err.codigo == "NIT_NO_ENCONTRADO"
    assert err.status_code == 404
    assert "9003189639" in err.mensaje


def test_proceso_no_encontrado():
    err = ProcesoNoEncontradoError("abc-123")
    assert err.codigo == "PROCESO_NO_ENCONTRADO"
    assert err.status_code == 404
    assert "abc-123" in err.mensaje


def test_entidad_no_encontrado():
    err = EntidadNoEncontradoError("9003189639")
    assert err.codigo == "ENTIDAD_NO_ENCONTRADA"
    assert err.status_code == 404


def test_proceso_en_proceso():
    err = ProcesoEnProcesoError("abc-123")
    assert err.codigo == "PROCESO_EN_PROCESO"
    assert err.status_code == 409
    assert "abc-123" in err.mensaje


def test_mcp_connection_error():
    err = MCPConnectionError("timeout")
    assert err.codigo == "MCP_CONNECT_FAIL"
    assert err.status_code == 503
    assert "timeout" in err.mensaje


def test_llm_unavailable():
    err = LLMUnavailableError()
    assert err.codigo == "LLM_UNAVAILABLE"
    assert err.status_code == 503
    assert "no est" in err.mensaje or "disponible" in err.mensaje


def test_config_invalida():
    err = ConfiguracionInvalidaError("LLM_KEY", "no puede estar vacía")
    assert err.codigo == "CONFIG_INVALIDA"
    assert err.status_code == 500
    assert "LLM_KEY" in err.mensaje


def test_mcp_timeout():
    err = MCPTimeoutError("timeout")
    assert err.codigo == "MCP_TIMEOUT"
    assert err.status_code == 504


def test_mcp_conn_refused():
    err = MCPConnectionRefusedError("refused")
    assert err.codigo == "MCP_CONN_REFUSED"
    assert err.status_code == 503


def test_mcp_page_error():
    err = MCPPageError("page fail")
    assert err.codigo == "MCP_PAGE_ERROR"
    assert err.status_code == 500


def test_oracle_query_fail():
    err = OracleQueryFailError("query failed")
    assert err.codigo == "ORACLE_QUERY_FAIL"
    assert err.status_code == 500


def test_oracle_timeout():
    err = OracleTimeoutError("timed out")
    assert err.codigo == "ORACLE_TIMEOUT"
    assert err.status_code == 504


def test_llm_timeout():
    err = LLMTimeoutError("timed out")
    assert err.codigo == "LLM_TIMEOUT"
    assert err.status_code == 504


def test_llm_rate_limit():
    err = LLMRateLimitError("rate limit")
    assert err.codigo == "LLM_RATE_LIMIT"
    assert err.status_code == 429


def test_llm_invalid_json():
    err = LLMInvalidJSONError("bad json")
    assert err.codigo == "LLM_INVALID_JSON"
    assert err.status_code == 500


def test_llm_all_providers_failed():
    err = LLMAllProvidersFailedError("all failed")
    assert err.codigo == "LLM_ALL_PROVIDERS_FAILED"
    assert err.status_code == 503


def test_pg_conn_error():
    err = PGConnError("conn failed")
    assert err.codigo == "PG_CONN_ERROR"
    assert err.status_code == 503


def test_pg_insert_fail():
    err = PGInsertFailError("insert failed")
    assert err.codigo == "PG_INSERT_FAIL"
    assert err.status_code == 500


def test_criterios_invalidos():
    err = CriteriosInvalidosError("criterios invalidos")
    assert err.codigo == "CRITERIOS_INVALIDOS"
    assert err.status_code == 422


def test_worker_timeout():
    err = WorkerTimeoutError("worker timeout")
    assert err.codigo == "WORKER_TIMEOUT"
    assert err.status_code == 504


def test_orchestration_fail():
    err = OrchestrationFailError("orchestration fail")
    assert err.codigo == "ORCHESTRATION_FAIL"
    assert err.status_code == 500


def test_hallazgo_no_encontrado():
    err = HallazgoNoEncontradoError("hall-123")
    assert err.codigo == "HALLAZGO_NO_ENCONTRADO"
    assert err.status_code == 404


def test_solicitud_invalida():
    err = SolicitudInvalidaError("solicitud invalida")
    assert err.codigo == "SOLICITUD_INVALIDA"
    assert err.status_code == 422


def test_lookup_error():
    err = LookupError("CIIU", "not found")
    assert err.codigo == "LOOKUP_ERROR"
    assert err.status_code == 500


def test_all_errors_inherit_fiscal_ia_error():
    for cls in [
        MCPTimeoutError, MCPConnectionRefusedError, MCPPageError,
        OracleQueryFailError, OracleTimeoutError,
        LLMTimeoutError, LLMRateLimitError, LLMInvalidJSONError, LLMAllProvidersFailedError,
        PGConnError, PGInsertFailError,
        CriteriosInvalidosError,
        WorkerTimeoutError, OrchestrationFailError,
        HallazgoNoEncontradoError, SolicitudInvalidaError, LookupError,
    ]:
        assert issubclass(cls, FiscalIAError)
