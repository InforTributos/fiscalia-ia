from domain.errors import (
    FiscalIAError, NITNoEncontradoError, ProcesoNoEncontradoError,
    ClienteNoEncontradoError, ProcesoEnProcesoError, MCPConnectionError,
    LLMUnavailableError, ConfiguracionInvalidaError,
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


def test_cliente_no_encontrado():
    err = ClienteNoEncontradoError("9003189639")
    assert err.codigo == "CLIENTE_NO_ENCONTRADO"
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
