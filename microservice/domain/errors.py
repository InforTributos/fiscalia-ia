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


class LLMUnavailableError(FiscalIAError):
    codigo = "LLM_UNAVAILABLE"
    status_code = 503

    def __init__(self, detalle: str = ""):
        super().__init__(f"El servicio de IA no está disponible{' - ' + detalle if detalle else ''}")


class ConfiguracionInvalidaError(FiscalIAError):
    codigo = "CONFIG_INVALIDA"
    status_code = 500

    def __init__(self, campo: str, detalle: str):
        super().__init__(f"Configuración inválida: {campo} — {detalle}")


class LookupError(FiscalIAError):
    codigo = "LOOKUP_ERROR"
    status_code = 500

    def __init__(self, entidad: str, detalle: str):
        super().__init__(f"Error de resolución: {entidad} — {detalle}")
