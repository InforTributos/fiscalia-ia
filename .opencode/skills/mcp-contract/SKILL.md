---
name: mcp-contract
description: Use when working with MCP integration — the buscar_contribuyentes and obtener_datos_fiscales tools, their parameters and output shapes, pagination, and classification logic.
---

# MCP Contract — FiscalIA

## Communication
- Transport: stdio (MCP Server as subprocess)
- Library: fastmcp Client
- Discovery: MCP Server exposes available tools on connect

## Tools

### `buscar_contribuyentes`
Gets candidate NITs based on fiscalization criteria.

| Parameter | Type | Description |
|---|---|---|
| `vigencia_ini` | DATE | Period start |
| `vigencia_fin` | DATE | Period end |
| `tipo_regimen` | VARCHAR2 | COMUN / SIMPLIFICADO |
| `actividades_economicas` | TABLE | CIIU code list |
| `periodo` | VARCHAR2 | Fiscal year |
| `page` | INT | Page number |
| `page_size` | INT | Records per page (default: 100) |

Output per NIT:
```json
{
  "nit": "9003189639",
  "score_peso": 75.5,
  "es_candidato": true,
  "razon": "Income discrepancy 45% between exogena and declared ICA for CIIU 4711"
}
```

### `obtener_datos_fiscales`
Gets full fiscal data for a single NIT.

| Parameter | Type | Description |
|---|---|---|
| `nit` | VARCHAR2 | Taxpayer NIT |
| `periodo` | VARCHAR2 | Fiscal year |

Output:
```json
{
  "nit": "9012345678",
  "razon_social": "COMERCIO XYZ S.A.S.",
  "ciiu": "4711",
  "regimen": "COMUN",
  "declaraciones_ica": [
    {"periodo": "2024-B1", "base_gravable": 50000000, "tarifa": 0.01, "impuesto": 500000}
  ],
  "exogena_dian": [{"periodo": "2024", "ingresos": 120000000}],
  "rues_estado": "ACTIVO"
}
```

## Pre-filtration Classification
After MCP data is received, the service classifies each NIT:
1. No ICA declarations → **OMISO**
2. Declarations match exogena → **EXACTO**
3. Declarations with anomalies → **INEXACTO**

Only OMISO and INEXACTO proceed to LLM analysis.
