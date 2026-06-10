# Intent — Microservicio Python OCI para FiscalIA

## Propósito
Construir el microservicio Python OCI que orquesta los agentes de IA (AGT-01 y AGT-03) para la fiscalización del Impuesto de Industria y Comercio (ICA) en Valledupar, con arquitectura hexagonal y LLM agnóstico.

## Stack
- FastAPI + litellm Router (fallback automático) + python-oracledb
- LLM: NVIDIA NIM (primary, Llama 3.3 70B) → fallback NVIDIA NIM (Llama 3.2 3B)
- Caché en memoria con TTL, logging JSON estructurado
- Despliegue: Docker / OCI Container Instance
- Base de datos: Oracle 19c+ (solo PL/SQL packages)
- No LangGraph en V1 — orquestación directa desde use cases

## Entregables
- API REST con 3 endpoints: `/analizar/{nit}`, `/score/{nit}`, `/health`
- Orquestación de datos (cruces + inconsistencias + SRF) + enriquecimiento con IA
- LLM agnóstico vía litellm con fallback NVIDIA NIM (70B → 3B)
- Conexión a Oracle DB con python-oracledb (pool con timeout 5s)
- Caché en memoria con TTL, retry con tenacity, degradación graceful
- Logging JSON por request (request_id, tiempo_ms, eventos)
- Tests (unitarios AAA, integración con LLM real, estrés Locust)
- Docker + docker-compose
- Documentación completa en docs/ (10 docs + diagramas PlantUML)

## Unidades (Work Packages)
1. U-01 Fundación: estructura hexagonal, conexión Oracle, health, Docker
2. U-02 Contrato PL/SQL + Domain: VOs, entities, ports, 4 adapters Oracle
3. U-03 Use Cases + LLM: analizar_contribuyente, calcular_score, litellm, DI
4. U-04 LLM real: pruebas con NVIDIA NIM y fallback, ajuste de prompts
5. U-05 Caching + logging + resiliencia: MemoryCache, middleware logging, JSON formatter
6. U-06 Tests + documentación final: cobertura, README, docs

## Quality Gates
- Tests unitarios ≥ 75% cobertura (excluye adapters Oracle/LLM por depender de externos)
- POST /analizar/{nit} < 90s con primary LLM
- Fallback degradado (sin LLM) < 5s
- Caché: segundo llamado < 1s
- Stress: 50 usuarios sin errores 5xx
- Sin API keys hardcodeadas
- OpenAPI/Swagger en /docs

## Modo operativo
HITL (Human-in-the-Loop) — supervisión humana obligatoria en calidad de hallazgos.
