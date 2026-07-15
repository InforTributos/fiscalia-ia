class FiscalIAError(Exception):
    codigo: str = "UNKNOWN_ERROR"
    status_code: int = 500
    mensaje: str = "Error interno del servidor"

    def __init__(self, mensaje: str | None = None):
        super().__init__(mensaje or self.mensaje)
        if mensaje:
            self.mensaje = mensaje


class NITNoEncontradoError(FiscalIAError):
    codigo = "NIT_NO_ENCONTRADO"
    status_code = 404

    def __init__(self, nit: str):
        super().__init__(f"El NIT {nit} no fue encontrado en el padrón de contribuyentes")


class ProcesoNoEncontradoError(FiscalIAError):
    codigo = "PROCESO_NO_ENCONTRADO"
    status_code = 404

    def __init__(self, proceso_id: str):
        super().__init__(f"El proceso {proceso_id} no fue encontrado")


class ClienteNoEncontradoError(FiscalIAError):
    codigo = "CLIENTE_NO_ENCONTRADO"
    status_code = 404

    def __init__(self, nit: str):
        super().__init__(f"El cliente con NIT {nit} no está registrado")


class ProcesoEnProcesoError(FiscalIAError):
    codigo = "PROCESO_EN_PROCESO"
    status_code = 409

    def __init__(self, proceso_id: str, mensaje: str | None = None):
        super().__init__(mensaje or f"Ya existe un proceso activo con los mismos criterios: {proceso_id}")


class MCPConnectionError(FiscalIAError):
    codigo = "MCP_CONNECT_FAIL"
    status_code = 503

    def __init__(self, detalle: str = ""):
        texto = "No se pudo conectar al servicio MCP (Oracle)"
        if detalle:
            texto += f": {detalle}"
        super().__init__(texto)


class MCPTimeoutError(FiscalIAError):
    codigo = "MCP_TIMEOUT"
    status_code = 504

    def __init__(self, detalle: str = ""):
        super().__init__(f"Tiempo de espera agotado en MCP (Oracle){' - ' + detalle if detalle else ''}")


class MCPConnectionRefusedError(FiscalIAError):
    codigo = "MCP_CONN_REFUSED"
    status_code = 503

    def __init__(self, detalle: str = ""):
        super().__init__(f"Conexión rechazada por MCP (Oracle){' - ' + detalle if detalle else ''}")


class MCPPageError(FiscalIAError):
    codigo = "MCP_PAGE_ERROR"
    status_code = 500

    def __init__(self, detalle: str = ""):
        super().__init__(f"Error de paginación en MCP (Oracle){' - ' + detalle if detalle else ''}")


class OracleQueryFailError(FiscalIAError):
    codigo = "ORACLE_QUERY_FAIL"
    status_code = 500

    def __init__(self, detalle: str = ""):
        super().__init__(f"Error en consulta Oracle{' - ' + detalle if detalle else ''}")


class OracleTimeoutError(FiscalIAError):
    codigo = "ORACLE_TIMEOUT"
    status_code = 504

    def __init__(self, detalle: str = ""):
        super().__init__(f"Tiempo de espera agotado en Oracle{' - ' + detalle if detalle else ''}")


class LLMUnavailableError(FiscalIAError):
    codigo = "LLM_UNAVAILABLE"
    status_code = 503

    def __init__(self, detalle: str = ""):
        super().__init__(f"El servicio de IA no está disponible{' - ' + detalle if detalle else ''}")


class LLMTimeoutError(FiscalIAError):
    codigo = "LLM_TIMEOUT"
    status_code = 504

    def __init__(self, detalle: str = ""):
        super().__init__(f"Tiempo de espera agotado en LLM{' - ' + detalle if detalle else ''}")


class LLMRateLimitError(FiscalIAError):
    codigo = "LLM_RATE_LIMIT"
    status_code = 429

    def __init__(self, detalle: str = ""):
        super().__init__(f"Límite de tasa excedido en LLM{' - ' + detalle if detalle else ''}")


class LLMInvalidJSONError(FiscalIAError):
    codigo = "LLM_INVALID_JSON"
    status_code = 500

    def __init__(self, detalle: str = ""):
        super().__init__(f"Respuesta JSON inválida del LLM{' - ' + detalle if detalle else ''}")


class LLMAllProvidersFailedError(FiscalIAError):
    codigo = "LLM_ALL_PROVIDERS_FAILED"
    status_code = 503

    def __init__(self, detalle: str = ""):
        super().__init__(f"Todos los proveedores LLM fallaron{' - ' + detalle if detalle else ''}")


class PGConnError(FiscalIAError):
    codigo = "PG_CONN_ERROR"
    status_code = 503

    def __init__(self, detalle: str = ""):
        super().__init__(f"Error de conexión a PostgreSQL{' - ' + detalle if detalle else ''}")


class PGInsertFailError(FiscalIAError):
    codigo = "PG_INSERT_FAIL"
    status_code = 500

    def __init__(self, detalle: str = ""):
        super().__init__(f"Error al insertar en PostgreSQL{' - ' + detalle if detalle else ''}")


class CriteriosInvalidosError(FiscalIAError):
    codigo = "CRITERIOS_INVALIDOS"
    status_code = 422

    def __init__(self, detalle: str = ""):
        super().__init__(f"Criterios de búsqueda inválidos{' - ' + detalle if detalle else ''}")


class WorkerTimeoutError(FiscalIAError):
    codigo = "WORKER_TIMEOUT"
    status_code = 504

    def __init__(self, detalle: str = ""):
        super().__init__(f"Tiempo de espera del worker agotado{' - ' + detalle if detalle else ''}")


class OrchestrationFailError(FiscalIAError):
    codigo = "ORCHESTRATION_FAIL"
    status_code = 500

    def __init__(self, detalle: str = ""):
        super().__init__(f"Error de orquestación del proceso{' - ' + detalle if detalle else ''}")


class ConfiguracionInvalidaError(FiscalIAError):
    codigo = "CONFIG_INVALIDA"
    status_code = 500

    def __init__(self, campo: str, detalle: str):
        super().__init__(f"Configuración inválida: {campo} — {detalle}")


class HallazgoNoEncontradoError(FiscalIAError):
    codigo = "HALLAZGO_NO_ENCONTRADO"
    status_code = 404

    def __init__(self, hallazgo_id: str):
        super().__init__(f"El hallazgo fiscal {hallazgo_id} no fue encontrado")


class SolicitudInvalidaError(FiscalIAError):
    codigo = "SOLICITUD_INVALIDA"
    status_code = 422

    def __init__(self, detalle: str):
        super().__init__(detalle)


class LookupError(FiscalIAError):
    codigo = "LOOKUP_ERROR"
    status_code = 500

    def __init__(self, entidad: str, detalle: str):
        super().__init__(f"Error de resolución: {entidad} — {detalle}")
