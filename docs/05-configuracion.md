# Configuración — FiscalIA Microservicio

## 1. Variables de Entorno

Todas las variables se configuran en un archivo `.env` en la raíz del proyecto o como variables de entorno en OCI Container Instance.

### 1.1. API

| Variable | Obligatorio | Default | Descripción |
|---|---|---|---|
| `API_PORT` | No | `8000` | Puerto donde escucha el microservicio |
| `API_HOST` | No | `0.0.0.0` | Host de escucha |
| `API_KEY` | **Sí** | - | API Key para autenticar llamadas desde APEX |

### 1.2. Oracle Database

| Variable | Obligatorio | Default | Descripción |
|---|---|---|---|
| `ORACLE_DSN` | **Sí** | - | DSN de conexión: `host:puerto/servicio` |
| `ORACLE_USER` | **Sí** | - | Usuario de base de datos |
| `ORACLE_PASSWORD` | **Sí** | - | Contraseña |

### 1.3. LLM

| Variable | Obligatorio | Default | Descripción |
|---|---|---|---|
| `LLM_MODE` | No | `primary_fallback` | `primary_only` o `primary_fallback` |
| `LLM_PRIMARY_PROVIDER` | **Sí** | `nvidia_nim` | Proveedor primario (ver docs/06-llm) |
| `LLM_PRIMARY_MODEL` | **Sí** | `meta/llama-3.3-70b-instruct` | Modelo primario |
| `LLM_PRIMARY_API_KEY` | **Sí** | - | API Key del proveedor primario |
| `LLM_PRIMARY_API_BASE` | No | `https://integrate.api.nvidia.com/v1` | URL base del proveedor (si aplica) |
| `LLM_FALLBACK_PROVIDER` | No | `nvidia_nim` | Proveedor de respaldo |
| `LLM_FALLBACK_MODEL` | No | `meta/llama-3.2-3b-instruct` | Modelo de respaldo (ligero 3B) |
| `LLM_FALLBACK_API_KEY` | No | - | API Key del respaldo |
| `LLM_MAX_TOKENS` | No | `4096` | Máximo de tokens por respuesta |
| `LLM_TIMEOUT` | No | `60` | Timeout en segundos |

### 1.4. Caché

| Variable | Obligatorio | Default | Descripción |
|---|---|---|---|
| `CACHE_TTL_SECONDS` | No | `3600` | TTL de caché en segundos (1 hora) |

### 1.5. Retry

| Variable | Obligatorio | Default | Descripción |
|---|---|---|---|
| `RETRY_MAX_ATTEMPTS` | No | `3` | Intentos máximos para llamadas LLM |
| `RETRY_BACKOFF_FACTOR` | No | `2` | Factor de backoff exponencial |
| `RETRY_TIMEOUT` | No | `60` | Timeout total de retry |

### 1.6. Logging

| Variable | Obligatorio | Default | Descripción |
|---|---|---|---|
| `LOG_LEVEL` | No | `INFO` | Nivel de logging: DEBUG, INFO, WARNING, ERROR |

---

## 2. Archivo `.env.example`

```env
# === API ===
API_PORT=8000
API_HOST=0.0.0.0
API_KEY=abc123...

# === ORACLE ===
ORACLE_DSN=host:1521/service
ORACLE_USER=user
ORACLE_PASSWORD=pass

# === LLM ===
LLM_MODE=primary_fallback
LLM_PRIMARY_PROVIDER=nvidia_nim
LLM_PRIMARY_MODEL=meta/llama-3.3-70b-instruct
LLM_PRIMARY_API_KEY=nvapi-...
LLM_PRIMARY_API_BASE=https://integrate.api.nvidia.com/v1
LLM_FALLBACK_PROVIDER=nvidia_nim
LLM_FALLBACK_MODEL=meta/llama-3.2-3b-instruct
LLM_FALLBACK_API_KEY=nvapi-...
LLM_MAX_TOKENS=4096
LLM_TIMEOUT=60

# === CACHE ===
CACHE_TTL_SECONDS=3600

# === RETRY ===
RETRY_MAX_ATTEMPTS=3
RETRY_BACKOFF_FACTOR=2
RETRY_TIMEOUT=60

# === LOG ===
LOG_LEVEL=INFO
```

---

## 3. Consideraciones de Seguridad

- **Nunca** comitear el archivo `.env` al repositorio (está en `.gitignore`)
- En **OCI Container Instance**, usar **OCI Vault** para almacenar las variables sensibles
- Rotar `API_KEY` y `LLM_PRIMARY_API_KEY` periódicamente
- `ORACLE_PASSWORD` debe cumplir la política de contraseñas de la base de datos

---

## 4. Configuración por Ambiente

| Ambiente | `LOG_LEVEL` | `CACHE_TTL` | `LLM_MODE` |
|---|---|---|---|
| Desarrollo | `DEBUG` | `60` (1 min) | `primary_only` |
| Pruebas | `INFO` | `300` (5 min) | `primary_fallback` |
| Producción | `INFO` | `3600` (1 hr) | `primary_fallback` |
