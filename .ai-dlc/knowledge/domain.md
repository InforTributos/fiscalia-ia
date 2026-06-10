# Domain Knowledge — Fiscalización ICA

## Impuesto de Industria y Comercio (ICA)
- Impuesto municipal colombiano sobre actividades comerciales, industriales y de servicios
- Periodicidad: bimestral o mensual según ingresos
- Tarifa: varía por municipio y actividad CIIU (Acuerdo Municipal)
- Base gravable: ingresos brutos

## Fuentes de Datos
- **Declaraciones ICA**: Sistema propio (Oracle) — ingresos declarados por CIIU
- **Exógena municipal**: Reporte anual de terceros (Oracle) — detalle de ingresos por cliente
- **DIAN**: Tablas temporales — datos externos del contribuyente
- **RUES**: Web service Confecámaras — estado mercantil de empresas

## Agentes
- **AGT-00 Orchestrator**: Coordina flujo (PL/SQL + APEX)
- **AGT-01 CrossCheck**: Cruces de información — llama a PL/SQL FISCAL_CROSS, enriquece con IA
- **AGT-02 OmisosDetect**: Detecta no declarantes (PL/SQL + UTL_MATCH, sin IA en V1)
- **AGT-03 InconsistencyAnalyzer**: Analiza inconsistencias — llama a PL/SQL FISCAL_INC, genera explicación IA
- **AGT-04 LegalDraft**: Diferido a versión SaaS futura

## Score de Riesgo Fiscal (SRF)
- 0-100, 4 componentes con pesos configurables en FISCAL_PESOS
- Diferencia exógena (35%) + Antigüedad omisión (20%) + Tarifa CIIU (25%) + Estado RUES (20%)
- Niveles: BAJO (<40), MEDIO (40-70), ALTO (>70)

## Arquitectura Hexagonal
- **api/**: Inbound adapters (FastAPI, routers, schemas, middleware, deps)
- **domain/**: Core del negocio (entities, value_objects, ports)
- **application/**: Casos de uso (analizar_contribuyente, calcular_score)
- **infrastructure/**: Outbound adapters (repos Oracle, litellm, cache)

## LLM Agnóstico (litellm Router con fallback automático)
- **Primary**: NVIDIA NIM — `meta/llama-3.3-70b-instruct` (70B params, alta calidad)
- **Fallback**: NVIDIA NIM — `meta/llama-3.2-3b-instruct` (3B params, rápido, misma API key)
- **Modo degradado**: responde en < 5s sin LLM cuando ambos fallan
- Configurable vía .env: `LLM_PRIMARY_PROVIDER`, `LLM_PRIMARY_MODEL`, `LLM_PRIMARY_API_KEY`
- Si fallback también falla → `_respuesta_degradada()` con explicación "no disponible"

## Caché en Memoria
- `MemoryCache` (singleton via DI en `deps.py`)
- Claves: `analisis:{nit}:{periodo}` y `score:{nit}:{periodo}`
- TTL configurable: `CACHE_TTL_SECONDS` (default 3600s = 1h)
- Segundo llamado con misma clave < 1ms (no toca LLM ni Oracle)
- Cache miss → llama LLM → guarda en caché

## Logging Estructurado
- Middleware `LoggingMiddleware` genera JSON por línea en stdout
- Cada request: `request_id` (UUID 8 chars), `event`, `method`, `path`, `status`, `tiempo_ms`
- Eventos: `request_start` y `request_end`
- Errores: `request_error` con mensaje de error
- Parseable por OCI Logging para alarmas y dashboards

## Conexión Oracle
- `oracledb.create_pool()` con `timeout=5` para fail rápido sin BD
- `_pool_attempted` flag: solo un intento de crear pool, luego retorna False
- Health endpoint detecta si Oracle está disponible y marca `status: degraded`

## Contrato PL/SQL
El microservicio llama 4 packages Oracle:
- `FISCAL_CROSS.obtener_cruces()` → cruces exógena vs ICA
- `FISCAL_INC.obtener_inconsistencias()` → inconsistencias detectadas
- `FISCAL_SCORE.obtener_srf()` → score con componentes
- `FISCAL_ANALISIS_IA.guardar()` → persistir resultados IA

## Tablas Oracle (prefijo FISCAL_)
FISCAL_CAMPANAS, FISCAL_EXPEDIENTES, FISCAL_CRUCES,
FISCAL_SCORE_RIESGO, FISCAL_OMISOS, FISCAL_INCONSISTENCIAS,
FISCAL_ANALISIS_IA, FISCAL_HITL_LOG, FISCAL_AUDIT_LOG, FISCAL_PESOS

## Stack Tecnológico
- Frontend: Oracle APEX 24.x
- Lógica negocio: PL/SQL Packages
- IA: Microservicio Python (FastAPI + litellm) en OCI Container
- BD: Oracle Database 19c+
- LLM: NVIDIA NIM (primary 70B → fallback 3B)
- Caché: En memoria (TTL 3600s)
- Logging: JSON estructurado stdout
- Despliegue: Docker + OCI Container Instance

## Metodología AI-DLC
- Intent: Construir microservicio Python OCI para FiscalIA
- Units: 6 (U-01 a U-06), corresponden a las fases F-01 a F-06
- Hats: Planner, Builder, Reviewer, TestWriter, Implementer
- Quality Gates: tests ≥ 75%, stress test 50 users, sin secrets hardcodeados, OpenAPI, cache TTL
