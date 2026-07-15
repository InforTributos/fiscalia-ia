# Spec: Tests de caracterizacion del modulo MCP

## Behaviors

### MCPClient (oracle_adapter.py)

| ID | Given | When | Then |
|----|-------|------|------|
| B01 | settings con MCP_SERVER_URL, MCP_TOKEN_URL, MCP_DB_USER, MCP_DB_PASSWORD configurados | Se instancia MCPClient() | self._url, self._token_url, self._user, self._password estan poblados con los valores de settings |
| B02 | MCPClient configurado con credenciales validas | Se llama _get_token() | Hace POST a MCP_TOKEN_URL con grant_type=password, username, password; retorna el access_token del JSON de respuesta |
| B03 | MCPClient configurado | Se llama call_tool("EXECUTE_SQL", {"query": "...", "bind_params": {"nit": "123"}}) | Obtiene token, configura headers Authorization Bearer, crea httpx.AsyncClient, establece sesion MCP via streamable_http_client, hace initialize, llama call_tool, parsea JSON del content[0].text y lo retorna |
| B04 | Llamada a call_tool retorna result.content vacio | Se procesa la respuesta | Retorna {} |
| B05 | Llamada a call_tool retorna content[0].text con JSON string | Se procesa la respuesta | Retorna el dict parseado de json.loads(text) |
| B06 | Llamada a call_tool retorna content[0].text con valor no-string | Se procesa la respuesta | Retorna el valor tal cual (sin json.loads) |
| B07 | MCPClient instanciado | Se llama close() | No hace nada (pass) |

### Pagination (pagination.py)

| ID | Given | When | Then |
|----|-------|------|------|
| B10 | NIT y periodo validos | Se llama obtener_datos_fiscales(client, "123", "2024") | Llama EXECUTE_SQL 3 veces: OBTENER_CONTRIBUYENTE_SQL, OBTENER_DECLARACIONES_SQL, OBTENER_EXOGENA_SQL; arma y retorna dict con nit, razon_social, ciiu, regimen, declaraciones_ica, exogena_dian, rues_estado |
| B11 | EXECUTE_SQL para contribuyente retorna vacio/nulo | Se procesa la respuesta | Retorna None |
| B12 | EXECUTE_SQL para contribuyente retorna lista de 1 fila | Se procesa la respuesta | Extrae row = result[0] |
| B13 | EXECUTE_SQL para contribuyente retorna dict individual | Se procesa la respuesta | Usa result directamente como row |
| B14 | Contribuyente con todos los campos | Se arma el resultado | dict incluye razon_social, ciiu, regimen, declaraciones_ica, exogena_dian, rues_estado con defaults seguros |
| B15 | Actividades economicas = ["4711", "4721"] | Se construye SQL en paginar_contribuyentes | Placeholders ":a0, :a1" se interpolan en el SQL; bind_params incluye a0="4711", a1="4721" |
| B16 | page_size=100 y hay 250 resultados | Itera paginacion | Yield 100 items, luego 100, luego 50, luego break |
| B17 | Una pagina retorna lista vacia | Itera paginacion | Termina el loop |
| B18 | EXECUTE_SQL retorna None/falsy | Itera paginacion | Termina el loop |
| B19 | offset incrementa por page_size en cada pagina | Itera paginacion | offset va 0, 100, 200, ... |

### AGT05MCPClient (client_adapter.py)

| ID | Given | When | Then |
|----|-------|------|------|
| B25 | AGT05MCPClient instanciado | Se llama buscar_contribuyentes(...) | Crea un MCPClient, llama paginar_contribuyentes con los mismos parametros, yield cada item del generator |
| B26 | AGT05MCPClient instanciado | Se llama obtener_datos(nit, periodo) | Delega a obtener_datos_fiscales(client, nit, periodo) |
| B27 | AGT05MCPClient instanciado | Se llama close() | No hace nada (pass) |

### Classify (classify.py)

| ID | Given | When | Then |
|----|-------|------|------|
| B30 | item con es_candidato=False | clasificar_nit(item) | Retorna ("EXACTO", mensaje) |
| B31 | item con es_omiso=True | clasificar_nit(item) | Retorna ("OMISO", razon o mensaje default) |
| B32 | item con score>=30, no omiso | clasificar_nit(item) | Retorna ("INEXACTO", razon o mensaje con score) |
| B33 | item con score<30, candidato, no omiso | clasificar_nit(item) | Retorna ("EXACTO", "Sin inconsistencias relevantes") |
| B34 | item con razon vacia, es_omiso | clasificar_nit(item) | Retorna ("OMISO", "No se encontraron declaraciones ICA para el periodo") |

### Analisis Task (analisis_task.py)

| ID | Given | When | Then |
|----|-------|------|------|
| B40 | Proceso con NITs omisos e inexactos | analizar_proceso(proceso_id, intento_id) | Itera todos los NITs, ejecuta orchestrator para cada uno, actualiza progreso, marca COMPLETADO |
| B41 | Un NIT falla con excepcion | Procesa el NIT | Captura Exception, inserta error_detalle, incrementa contador de errores, continua con siguiente NIT |
| B42 | Todos los NITs procesados sin errores | Finaliza | Estado final = "COMPLETADO" |
| B43 | Al menos un NIT fallo | Finaliza | Estado final = "ERROR" |

## Edge Cases

| ID | Scenario | Expected Behavior |
|----|----------|-------------------|
| E01 | MCP_TOKEN_URL retorna HTTP 401 | _get_token debe propagar httpx.HTTPStatusError |
| E02 | Token response sin campo access_token | _get_token debe propagar KeyError |
| E03 | call_tool con arguments=None | Se pasa {} al session.call_tool |
| E04 | obtener_datos_fiscales con NIT sin declaraciones | declaraciones_ica = [] (lista vacia, seguro) |
| E05 | obtener_datos_fiscales con NIT sin exogena | exogena_dian = [] (lista vacia, seguro) |
| E06 | paginar_contribuyentes con actividades_economicas=[] | Placeholders string queda vacio "; SQL falla en Oracle (pero no es responsabilidad de este test)" — la funcion construye ":a0, :a1..." con 0 items |
| E07 | analisis_task con 0 rows en proceso_detalle | Loop no itera; estados se actualizan a COMPLETADO |

## Constraints

- Todos los servicios externos deben ser mockeados (httpx, mcp session, streamable_http_client, settings, PostgresProcesoRepo, LLMService)
- Los tests usan `@patch` a nivel de modulo para sustituir dependencias externas
- No se requiere conexion real a Oracle MCP Server ni PostgreSQL
- Los tests deben ejecutarse con `PYTHONPATH=microservice pytest tests/unit/ -v`
- Formato AAA (Arrange-Act-Assert) obligatorio
