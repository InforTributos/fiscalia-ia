# Domain Knowledge — Fiscalización ICA

## Impuesto de Industria y Comercio (ICA)
- Impuesto municipal colombiano sobre actividades comerciales, industriales y de servicios
- Periodicidad: bimestral o mensual según ingresos
- Tarifa: varía por municipio y actividad CIIU (Acuerdo Municipal)
- Base gravable: ingresos brutos
- Normativa: Ley 14 de 1983, Ley 1819 de 2016, Ley 2277 de 2022

## Fuentes de Datos
- **Declaraciones ICA**: Sistema Oracle tributario — ingresos declarados por período y CIIU
- **Exógena municipal**: Reporte anual de terceros — detalle de ingresos por cliente
- **DIAN**: Tablas temporales — datos externos del contribuyente
- **RUES**: Cámara de Comercio — estado mercantil de empresas
- **Acceso**: Vía MCP Server (Model Context Protocol) — el microservicio no conecta directo a Oracle

## Agentes
- **AGT-00 Orchestrator**: Coordina flujo de análisis — implementado en `tasks/analisis_task.py` + `application/use_cases/orquestar_proceso.py`
- **AGT-01 CrossCheck**: Cruces de información — implementado en `domain/services/crosscheck_service.py` (cálculo SRF, clasificación, extracción inconsistencias)
- **AGT-02 OmisosDetect**: Detecta no declarantes — implementado en `crosscheck_service.clasificar_por_datos()`
- **AGT-03 InconsistencyAnalyzer**: Analiza inconsistencias — implementado en `domain/services/inconsistency_service.py` (nivel de riesgo)
- **AGT-04 LegalDraft**: Diferido a versión SaaS futura
- **AGT-05 MCP Client**: Gestiona conexión stdio con MCP Server — implementado en `infrastructure/mcp/oracle_adapter.py`

## Score de Riesgo Fiscal (SRF)
- 0-100, 4 componentes con pesos fijos en `crosscheck_service.py`
- Diferencia exógena (35%) + Antigüedad omisión (20%) + Tarifa CIIU (25%) + Estado RUES (20%)
- Niveles: BAJO (<40), MEDIO (40-70), ALTO (>70)

## Arquitectura Hexagonal (Ports & Adapters)
- **domain/**: Core del negocio (ports ABCs, services, errors)
- **application/**: Casos de uso (orquestar_proceso)
- **infrastructure/llm/**: Proveedores LLM concretos + fallback chain
- **infrastructure/persistence/**: asyncpg pool + queries + repositorios
- **infrastructure/mcp/**: Cliente MCP stdio + paginación + clasificación
- **routers/**: Inbound adapters (FastAPI endpoints)
- **middleware/**: Error handler, logging, rate limiter

## LLM Provider Agnostic con Fallback 3 Tiers
- **Tier 1 (pago)**: Anthropic Claude (`claude-sonnet-4-20250506`) o OpenAI GPT (`gpt-4o`) — configurable vía `LLM_TIER1_PROVIDER`
- **Tier 2 (gratis)**: NVIDIA NIM — `qwen/qwen2.5-7b-instruct`
- **Tier 3 (gratis)**: HuggingFace — `Qwen/Qwen2.5-7B-Instruct`
- Fallback automático: si Tier 1 falla → Tier 2 → Tier 3 → respuesta degradada
- Implementación: `LLMProvider` ABC + `LLMService` con tenacity retry
- No usa litellm — implementación custom con providers directos

## Caché en Memoria
- `MemoryCache` (singleton en `cache/response_cache.py`)
- Claves: `analisis:{nit}:{periodo}`
- TTL configurable: `CACHE_TTL_SECONDS` (default 3600s = 1h)
- Segundo llamado con misma clave no toca LLM ni MCP
- Cache miss → llama LLM → guarda en caché

## Logging Estructurado
- Middleware `LoggingMiddleware` genera JSON por línea en stdout
- Cada request: `request_id`, `event`, `method`, `path`, `status`, `tiempo_ms`
- Parseable por OCI Logging para alarmas y dashboards

## Persistencia PostgreSQL
- Pool asyncpg con `min_size=4, max_size=20, timeout=5` (configurable)
- Tablas: `clientes`, `procesos`, `proceso_intentos`, `proceso_detalle`, `proceso_errores`, `proceso_detalle_errores`
- Repositorios: `PostgresProcesoRepo`, `PostgresContribuyenteRepo` (implementan ABCs en `domain/ports/`)
- Conexión vía `infrastructure/persistence/connection.py` (lazy pool singleton)

## Contrato MCP (reemplaza PL/SQL)
El microservicio NO llama PL/SQL directo. Obtiene datos vía MCP Server (stdio):
- Tool `buscar_contribuyentes`: criterios → NITs candidatos con score
- Tool `obtener_datos_fiscales`: NIT + periodo → datos fiscales completos

## Stack Tecnológico
- Framework: FastAPI (Python 3.14+)
- Persistencia: PostgreSQL 16+ (asyncpg)
- LLM: Anthropic / OpenAI / NVIDIA NIM / HuggingFace (4 providers, 3 tiers)
- MCP: Model Context Protocol vía stdio (fastmcp)
- Caché: En memoria (TTL 3600s)
- Logging: JSON estructurado stdout
- Errores: Jerarquía FiscalIAError con códigos HTTP
- Calidad: ruff, pytest-cov, pytest-html, factory-boy
- Despliegue: Docker + OCI Container Instance

## Metodología AI-DLC
- Intent: Construir microservicio Python OCI para FiscalIA
- Units: 6 (U-01 a U-06), corresponden a fases de implementación
- Hats: Planner, Builder, Reviewer, TestWriter, Implementer
- Quality Gates: tests ≥ 80%, sin secrets hardcodeados, OpenAPI, cache TTL
