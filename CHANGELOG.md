# Changelog — FiscalIA

> **Formato:** [Keep a Changelog](https://keepachangelog.com/)  
> **Versionado:** [SemVer](https://semver.org/)

---

## [2.0.0] — 2026-07-23

### Added
- Sistema completo de fiscalización ICA (R1-R10) con motor de reglas fiscal
- Score de Riesgo Fiscal (SRF) con 4 componentes
- Análisis comportamental vs pares del mismo CIIU
- Patrones temporales (caída abrupta, tendencia, divergencia exógena)
- Score unificado (comportamental + SRF + reglas + red + temporal)
- Hallazgos fiscales con scoring automático y ciclo HITL
- Intermediación DIAN como fuente de datos (GI_G_INTERMEDIA_DIAN)
- 13 tests de regresión para R3 (test_exogena_fix.py)

### Changed
- **R3 fix**: VLOR_RTNCION → VLOR_BSE, filtro `cdgo_exgna_tpo_rgstro = 'RD'` (2026-07-23)
- **pagination.py fix**: CASE codes `'RECIBIDA'/'PRACTICADA'` → `'RD'/'RP'`
- Conexión Oracle directa vía `oracledb` pool async (reemplaza MCP HTTP)
- Documentación actualizada: fuentes de datos Oracle documentadas en Apéndice A

### Fixed
- R3 (brecha exógena) nunca se disparaba: comparaba retención ($40k) vs base ($100M)
- pagination.py: columnas `retenciones_exogena_*` siempre devolvían 0 (CASE codes incorrectos)

### Technical Debt
- R4 (facturación electrónica): fuente identificada, falta conectar
- R5 (contratista estatal): requiere integración SECOP
- R8 (atípico sectorial): requiere diseño de acumulador
- Periodo hardcodeado en `orquestar_proceso.py`
- Procrastinate para tasks persistentes (hoy: `asyncio.create_task`)

---

## [1.0.0] — 2026-06

### Added
- Microservicio FastAPI base con arquitectura hexagonal
- Conexión Oracle vía MCP HTTP (posteriormente migrada a `oracledb` directo)
- Proveedores LLM: Anthropic, OpenAI, NVIDIA NIM, HuggingFace
- PostgreSQL con pool asyncpg y 6 tablas
- Endpoints REST: `/health`, `/analizar/{nit}`, `/proceso`
- Tests unitarios base (~109)
- Documentación inicial

### Infrastructure
- OCI Container Instance deployment
- OCI Logging con JSON structured logs
- Caché en memoria con TTL
- Rate limiter in-memory

---

[2.0.0]: https://github.com/Informatica-y-Tributos/fiscalia-ia/releases/tag/v2.0.0
[1.0.0]: https://github.com/Informatica-y-Tributos/fiscalia-ia/releases/tag/v1.0.0
