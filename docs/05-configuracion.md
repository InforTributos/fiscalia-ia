# Configuración — FiscalIA Microservicio

## 1. Variables de Entorno

Todas las variables se configuran en un archivo `.env` en la raíz del proyecto o como variables de entorno en OCI Container Instance.

### 1.1. API

| Variable | Obligatorio | Default | Descripción |
|---|---|---|---|
| `API_PORT` | No | `8000` | Puerto donde escucha el microservicio |
| `API_HOST` | No | `0.0.0.0` | Host de escucha |

### 1.2. PostgreSQL

| Variable | Obligatorio | Default | Descripción |
|---|---|---|---|
| `POSTGRES_HOST` | **Sí** | `localhost` | Host de PostgreSQL |
| `POSTGRES_PORT` | No | `5432` | Puerto de PostgreSQL |
| `POSTGRES_DB` | **Sí** | `fiscalia` | Nombre de la base de datos |
| `POSTGRES_USER` | **Sí** | `fiscalia` | Usuario |
| `POSTGRES_PASSWORD` | **Sí** | - | Contraseña (validada contra placeholder `changeme`) |

### 1.3. LLM — Tier 1 (pago)

| Variable | Obligatorio | Default | Descripción |
|---|---|---|---|
| `LLM_TIER1_PROVIDER` | **Sí** | `anthropic` | Proveedor: `anthropic` o `openai` |
| `LLM_TIER1_API_KEY` | **Sí** | - | API Key (validada contra `changeme`) |
| `LLM_TIER1_MODEL` | No | `claude-sonnet-4-20250506` | Modelo |

### 1.4. LLM — Tier 2 (gratis, NVIDIA NIM)

| Variable | Obligatorio | Default | Descripción |
|---|---|---|---|
| `LLM_TIER2_API_KEY` | **Sí** (si se usa) | - | API Key de NVIDIA NIM |
| `LLM_TIER2_MODEL` | No | `qwen/qwen2.5-7b-instruct` | Modelo |

### 1.5. LLM — Tier 3 (gratis, HuggingFace)

| Variable | Obligatorio | Default | Descripción |
|---|---|---|---|
| `LLM_TIER3_API_KEY` | **Sí** (si se usa) | - | Token de HuggingFace |
| `LLM_TIER3_MODEL` | No | `Qwen/Qwen2.5-7B-Instruct` | Modelo |

### 1.6. Caché

| Variable | Obligatorio | Default | Descripción |
|---|---|---|---|
| `CACHE_TTL_SECONDS` | No | `3600` | TTL de caché en segundos (1 hora) |

### 1.7. Retry

| Variable | Obligatorio | Default | Descripción |
|---|---|---|---|
| `RETRY_MAX_ATTEMPTS` | No | `3` | Intentos máximos para llamadas LLM |
| `RETRY_BACKOFF_FACTOR` | No | `2` | Factor de backoff exponencial |
| `RETRY_TIMEOUT` | No | `60` | Timeout total de retry en segundos |

### 1.8. Background Tasks

| Variable | Obligatorio | Default | Descripción |
|---|---|---|---|
| `MAX_CONCURRENT_PROCESSES` | No | `5` | Procesos simultáneos máximos |
| `PROCESS_TIMEOUT_MINUTES` | No | `30` | Timeout por proceso en minutos |

### 1.9. Logging

| Variable | Obligatorio | Default | Descripción |
|---|---|---|---|
| `LOG_LEVEL` | No | `INFO` | Nivel: DEBUG, INFO, WARNING, ERROR |

---

## 2. Archivo `.env.example`

```env
# === API ===
API_PORT=8000
API_HOST=0.0.0.0

# === PostgreSQL ===
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=fiscalia
POSTGRES_USER=fiscalia
POSTGRES_PASSWORD=

# === LLM Tier 1 (pago) ===
LLM_TIER1_PROVIDER=anthropic
LLM_TIER1_API_KEY=
LLM_TIER1_MODEL=claude-sonnet-4-20250506

# === LLM Tier 2 (gratis — NVIDIA NIM) ===
LLM_TIER2_API_KEY=
LLM_TIER2_MODEL=qwen/qwen2.5-7b-instruct

# === LLM Tier 3 (gratis — HuggingFace) ===
LLM_TIER3_API_KEY=
LLM_TIER3_MODEL=Qwen/Qwen2.5-7B-Instruct

# === Cache ===
CACHE_TTL_SECONDS=3600

# === Retry ===
RETRY_MAX_ATTEMPTS=3
RETRY_BACKOFF_FACTOR=2
RETRY_TIMEOUT=60

# === Background Tasks ===
MAX_CONCURRENT_PROCESSES=5
PROCESS_TIMEOUT_MINUTES=30

# === Log ===
LOG_LEVEL=INFO
```

---

## 3. Validación al Startup

`config.py` valida al arrancar que ninguna API key ni contraseña tenga el valor `"changeme"`. Si se detecta, levanta `ConfiguracionInvalidaError` con el nombre de la variable ofensiva.

Esto evita despliegues accidentales con claves placeholder.

---

## 4. Consideraciones de Seguridad

- **Nunca** comitear el archivo `.env` al repositorio (está en `.gitignore`)
- En **OCI Container Instance**, usar **OCI Vault** para almacenar variables sensibles
- Rotar `LLM_TIER1_API_KEY`, `LLM_TIER2_API_KEY`, `LLM_TIER3_API_KEY` y `POSTGRES_PASSWORD` periódicamente
- El placeholder `changeme` es rechazado automáticamente por pydantic

---

## 5. Configuración por Ambiente

| Ambiente | `LOG_LEVEL` | `CACHE_TTL` | `MAX_CONCURRENT_PROCESSES` |
|---|---|---|---|
| Desarrollo | `DEBUG` | `60` (1 min) | `2` |
| Pruebas | `INFO` | `300` (5 min) | `5` |
| Producción | `INFO` | `3600` (1 hr) | `5` |
