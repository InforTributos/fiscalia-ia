# Oracle Autonomous AI Database MCP Server

> Scrapeado desde docs.oracle.com — Junio 2026  
> URL original: https://docs.oracle.com/es-ww/iaas/autonomous-database-serverless/doc/mcp-server.html

---

## ¿Qué es?

Servidor **gestionado y multiinquilino** de Oracle que expone tools de Autonomous AI Database vía MCP sobre HTTP. No requiere infraestructura propia de servidor MCP.

## Diferencias con el MCP de FiscalIA

| Aspecto | Oracle MCP Server | FiscalIA (nuestro) |
|---|---|---|
| Tipo | Remoto (managed) | Local (stdio subprocess) |
| Transporte | Streamable HTTP + SSE | stdio |
| Tools | `DBMS_CLOUD_AI_AGENT.CREATE_TOOL` (PL/SQL) | `fastmcp.Client` + Python |
| Autenticación | OAuth 2.1 / Bearer Token (1h) | No aplica (comunicación interna) |
| Clientes | Claude Desktop, Cline, OCI Agent | FastAPI (nuestro microservicio) |
| Activación | Free-form tag en OCI Console | Init del subprocess |

## Activación

```bash
# Tag para activar MCP Server en la BD
Tag Name: adb$feature
Tag Value: {"name":"mcp_server","enable":true}

# Desactivar
Tag Value: {"name":"mcp_server","enable":false}
```

## URL del Endpoint

```
https://dataaccess.adb.{region}.oraclecloudapps.com/adb/mcp/v1/databases/{database-ocid}
```

Para puntos finales privados, usar el `hostname_prefix` de la URL de private endpoint.

## Autenticación

### OAuth 2.1 (Claude Desktop, Cline)
- Muestra login prompt con usuario/contraseña de BD
- No requiere token explícito

### Bearer Token
```bash
curl --location 'https://dataaccess.adb.{region}.oraclecloudapps.com/adb/auth/v1/databases/{database-ocid}/token' \
  --header 'Content-Type: application/json' \
  --data '{
    "grant_type":"password",
    "username":"<db-user>",
    "password":"<db-password>"
  }'
```
Token válido **1 hora**.

## Configuración en Clientes

### Claude Desktop
```json
{
  "mcpServers": {
    "mcp_server": {
      "command": "/opt/homebrew/bin/npx",
      "args": ["-y", "mcp-remote", "https://dataaccess.adb.{region}.oraclecloudapps.com/adb/mcp/v1/databases/{ocid}", "--allow-http"],
      "transport": "streamable-http"
    }
  }
}
```

### VSCode + Cline
```json
{
  "mcpServers": {
    "database": {
      "timeout": 300,
      "type": "streamableHttp",
      "url": "https://dataaccess.adb.{region}.oraclecloudapps.com/adb/mcp/v1/databases/{ocid}"
    }
  }
}
```

## Crear Tools MCP

Se usa PL/SQL. Dos pasos: crear función + registrar tool.

### 1. Función PL/SQL
```sql
CREATE OR REPLACE FUNCTION list_schemas(offset NUMBER, limit NUMBER) RETURN CLOB AS ...
```

### 2. Registrar como tool MCP
```sql
BEGIN
  DBMS_CLOUD_AI_AGENT.CREATE_TOOL(
    tool_name  => 'LIST_SCHEMAS',
    attributes => '{
      "instruction": "Returns list of schemas",
      "function": "LIST_SCHEMAS",
      "tool_inputs": [
        {"name":"offset","description":"Pagination offset"},
        {"name":"limit","description":"Page size"}
      ]
    }'
  );
END;
```

### Tools de ejemplo incluidas en la doc
| Tool | Descripción |
|---|---|
| `LIST_SCHEMAS` | Lista esquemas no mantenidos por Oracle |
| `LIST_OBJECTS` | Lista objects (tablas, vistas, etc.) de un schema |
| `GET_OBJECT_DETAILS` | Metadatos de un objeto (columnas, índices, constraints) |
| `EXECUTE_SQL` | Ejecuta SELECT read-only (paginado) |

## Arquitectura (3 capas)

1. **Unified Security Layer**: ACL, Private Endpoints, VPD policies, DB roles
2. **Multi-tenant MCP Server**: Sin gestión de infraestructura, audit logging
3. **Select AI Agent Framework**: Tools PL/SQL, lifecycle management

## Versiones Soportadas
- Autonomous AI Database **26ai** y **19c**
- Clientes MCP con **Streamable HTTP** + OAuth 2.1
- Java soportado (JAVAVM), **JavaScript/MLE no soportado**

## Referencias
- [Página principal MCP Server](https://docs.oracle.com/es-ww/iaas/autonomous-database-serverless/doc/mcp-server.html)
- [Select AI Agent](https://docs.oracle.com/es-ww/iaas/autonomous-database-serverless/doc/select-ai-agent1.html)
- [DBMS_CLOUD_AI_AGENT Package](https://docs.oracle.com/es-ww/iaas/autonomous-database-serverless/doc/dbms-cloud-ai-agent-package.html)
