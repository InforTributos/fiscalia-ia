---
tags: [gotchas, lessons-learned]
---

# Lecciones Aprendidas — FiscalIA

> [!tip] Colección de comportamientos no obvios
> Si encuentras algo que te tomó tiempo descubrir, agrégalo aquí.

---

## PYTHONPATH

`PYTHONPATH=microservice` es **requerido** para todos los comandos de pytest. El `conftest.py` agrega `microservice/` al `sys.path`, pero la cobertura necesita que se especifique explícitamente.

```bash
# ✅ Correcto
PYTHONPATH=microservice pytest tests/unit/ --cov=microservice

# ❌ Incorrecto — falla por imports
pytest tests/unit/
```

> [!danger] Error común
> Olvidar `PYTHONPATH=microservice` es el error más frecuente al correr tests.

## Coverage sin infra real

La cobertura topa en **~72%** sin conexiones reales a PostgreSQL, MCP Server y LLM providers. No forzar el gate de 80% cuando solo corren tests unitarios.

> [!note] Gate 80% en CI
| El gate `--cov-fail-under=80` solo se alcanza en CI con mocks completos o en integración real.

## asyncpg pool lifecycle

El pool DEBE cerrarse al detener la aplicación. FastAPI lifespan lo maneja, pero si se crea un pool fuera del lifespan, queda abierto.

```python
# ✅ Correcto — via lifespan
await get_pool()   # startup
await close_pool() # shutdown
```

## CRLF en Windows

Git muestra warnings de CRLF en Windows. Es normal — el proyecto no tiene `.gitattributes`.

```
warning: in the working copy of 'archivo.py', LF will be replaced by CRLF
```

> [!info] Ignorar
| Estos warnings son inofensivos. No intentar "corregirlos".

## MCP no es Oracle directo

El microservicio **nunca** conecta directo a Oracle. Todos los datos fiscales se obtienen vía [[../docs/03-contrato-mcp]].

```python
# ❌ Incorrecto
import oracledb

# ✅ Correcto
from infrastructure.mcp.oracle_adapter import MCPClient
```

## Importación de repos en routers

Los routers instancian `PostgresProcesoRepo()` a nivel de módulo, no dentro de funciones. Si la conexión falla en startup, el error se dispara al importar el módulo. Es intencional (fail fast).

```python
# routers/proceso.py
repo = PostgresProcesoRepo()  # module level, not lazy
```

## Naming de env vars

| Contexto | Prefijo |
|---|---|
| LLM Tier 1 | `LLM_TIER1_*` |
| LLM Tier 2 | `LLM_TIER2_*` |
| LLM Tier 3 | `LLM_TIER3_*` |
| PostgreSQL | `POSTGRES_*` |
| Pool | `POOL_MIN_SIZE`, `POOL_MAX_SIZE`, `POOL_TIMEOUT` |

> [!warning] No usar nombres viejos
| `LLM_PRIMARY_*` o `LLM_FALLBACK*` son del plan V1 y no corresponden al código actual.

## Model Qwen: casing importa

| Plataforma | Identificador |
|---|---|
| NVIDIA NIM | `qwen/qwen2.5-7b-instruct` (minúsculas) |
| HuggingFace | `Qwen/Qwen2.5-7B-Instruct` (PascalCase) |

Los valores en `.env` deben coincidir exactamente con lo que cada API espera.

## El periodo está hardcodeado

`orquestar_proceso.py` tiene `periodo="2024"` fijo. Ver [[TODO]] para el estado de esta deuda técnica.

## .env.example en la raíz, no en microservice/

El `.env.example` está en la raíz del repo, no en `microservice/.env.example`. El `config.py` busca `.env` en el CWD, que es `microservice/` al correr la app. Copiar correctamente:

```bash
cp .env.example microservice/.env   # ✅
```

## pydantic-settings: extra: ignore

`config.py:51` tiene `"extra": "ignore"`. Si se escribe mal un nombre de variable en `.env`, no se muestra error. Verificar nombres contra [[CONTEXT#Variables de Entorno]].

## Settings singleton a module level

```python
# config.py
settings = Settings()  # ← instanciado al importar
```

Cualquier `from config import settings` ya tiene los valores cargados. No instanciar `Settings()` de nuevo.

## LLM Tier 1 puede ser anthropic u openai

`LLM_TIER1_PROVIDER` default es `anthropic`. Para cambiar a OpenAI:

```env
LLM_TIER1_PROVIDER=openai
LLM_TIER1_MODEL=gpt-4o
```

`LLM_TIER1_API_BASE` es opcional (None) — solo para self-hosted.

## Niveles SRF: 3 bandas

Score 0-100, definido en `inconsistency_service.py`:
- BAJO: < 40
- MEDIO: 40-70
- ALTO: > 70

No confundir con los estados del proceso (PENDIENTE, PREFILTRANDO, etc.) que son independientes.

## Retry config: backoff factor 2

```python
RETRY_MAX_ATTEMPTS=3
RETRY_BACKOFF_FACTOR=2
RETRY_TIMEOUT=60
```

Intentos: 0s → 2s → 4s → abort (3 intentos totales, 2 retrasos con backoff).

## `contribuyente_nit` vs `entidad_nit` — naming convention

Tres tablas usan NITs, pero con nombres distintos según su rol semántico:

| Contexto | Columna | Significado |
|---|---|---|
| `proceso_detalle.contribuyente_nit` | `contribuyente_nit` | NIT del contribuyente fiscalizado |
| `proceso_detalle_errores.contribuyente_nit` | `contribuyente_nit` | NIT del contribuyente asociado al error |
| `hallazgos_fiscales.contribuyente_nit` | `contribuyente_nit` | NIT del contribuyente del hallazgo |
| `entidades_fiscalizadoras.nit` | `nit` (sin prefijo) | NIT de la entidad fiscalizadora (municipio) |
| API request/response | `entidad_nit` | NIT de la entidad fiscalizadora en JSON |

Regla: si el NIT se refiere al **contribuyente investigado**, es `contribuyente_nit`. Si se refiere a la **entidad fiscalizadora** (municipio), es `nit` en DB y `entidad_nit` en API. Las migraciones `010` y `011` aplicaron estos cambios.

## Commit format: hats AI-DLC

```bash
git commit -m "builder: U-03 - implementar endpoint POST /proceso"
```

Ver [[DECISIONS#9. Commits: Formato AI-DLC con hats]] para más detalles.

## AI-DLC Knowledge: .ai-dlc/knowledge/domain.md

El conocimiento del dominio ICA (SRF, agentes AGT-00 a AGT-05, CIIU) está en `.ai-dlc/knowledge/domain.md`. Referenciado desde [[CONTEXT]] vía enlace `[[../.ai-dlc/knowledge/domain]]`.

## NVIDIA NIM: 40 RPM y 5K credits

| Aspecto | Detalle |
|---|---|
| Rate limit | 40 requests/min por modelo |
| Créditos gratis | 5,000 totales (1,000 al registrar + 4,000 con email empresarial) |
| Alcance | ~2,500-5,000 análisis según tamaño del prompt |
| Producción | Requiere NVIDIA AI Enterprise license o self-hosting |

## HuggingFace: selección automática de provider

HF usa política `:fastest` — selecciona automáticamente el provider más rápido entre SambaNova, Together AI, Fireworks AI, Nebius, Novita. El mismo modelo Qwen2.5-7B corre en múltiples providers.

## Planes v1 y v2.1 son idénticos

Ambos archivos en `../Planes de trabajo/fiscalIA/` son copia exacta. El plan v2.1 está en `.opencode/plans/` para referencia del agente, sin cambios sobre v1. No hay diferencias que trackear.

## LangGraph en plan pero no en código

El plan menciona LangGraph para orquestación (`agents/orchestrator.py`). El código real usa `application/use_cases/orquestar_proceso.py` con `asyncio.create_task`. LangGraph nunca se implementó.

## Procrastinate no implementado

El plan recomienda Procrastinate (cola PostgreSQL). El código actual usa `asyncio.create_task` — las tasks se pierden si el contenedor cae. La migración está pendiente. Ver [[TODO]].
