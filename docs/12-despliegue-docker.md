# Despliegue Docker — FiscalIA

Guía paso a paso para desplegar FiscalIA en un servidor con Docker y OPA (Open Policy Agent).

## 1. Requisitos

- Servidor Linux con Docker Engine
- Imágenes base permitidas por OPA: `python:3.14-slim`
- PostgreSQL 17 (en contenedor Docker o instalado directo)
- Acceso a Oracle DB (`99.0.5.109:1521`)
- API Keys: NVIDIA NIM (Tier 1), HuggingFace (Tier 3)

## 2. Estructura del Proyecto

```
fiscalia-ia/
├── docker-compose.yml       # Orquestación de servicios
├── Dockerfile               # Imagen de la API
├── .dockerignore            # Exclusión de archivos del build context
├── .env                     # Variables de entorno (no versionado)
├── microservice/            # Código de la aplicación
└── docs/                    # Documentación
```

## 3. Variables de Entorno (`.env`)

```env
# === API ===
API_PORT=8001

# === PostgreSQL ===
POSTGRES_HOST=99.0.5.213
POSTGRES_PORT=5433
POSTGRES_DB=fiscalia
POSTGRES_USER=admin
POSTGRES_PASSWORD=A

# === LLM Tier 1 (NVIDIA NIM) ===
LLM_TIER1_PROVIDER=nvidia_nim
LLM_TIER1_API_KEY=nvapi-...

# === LLM Tier 2 (NVIDIA NIM) ===
LLM_TIER2_API_KEY=nvapi-...

# === LLM Tier 3 (HuggingFace) ===
LLM_TIER3_API_KEY=hf_...

# === Oracle Database ===
ORACLE_HOST=99.0.5.109
ORACLE_PORT=1521
ORACLE_SERVICE=genesys01
ORACLE_USER=genesys
ORACLE_PASSWORD=...
```

## 4. Paso a Paso — Despliegue

### 4.1. Clonar y sincronizar

```bash
cd /DATOS01/docker/docker01
git clone https://github.com/InforTributos/fiscalia-ia.git
cd fiscalia-ia
git checkout main
```

### 4.2. Traer la rama actualizada

```bash
git fetch origin
git reset --hard origin/main
```

### 4.3. Etiquetar imágenes de terceros al namespace permitido por OPA

Si el OPA solo permite imágenes bajo `infortributos/`:

```bash
docker tag postgres:17.7 infortributos/postgres:17.7
```

### 4.4. Crear infraestructura base

```bash
docker network create db_default 2>/dev/null
docker volume create pgdata 2>/dev/null
```

### 4.5. Build de la imagen de la API

```bash
DOCKER_BUILDKIT=0 docker build --no-cache -t infortributos/fiscalia-api:latest .
```

### 4.6. Levantar PostgreSQL

```bash
docker run -d --name fiscalia-postgres \
  --restart unless-stopped \
  -p 5433:5432 \
  -e POSTGRES_DB=fiscalia \
  -e POSTGRES_USER=admin \
  -e POSTGRES_PASSWORD=A \
  -v pgdata:/var/lib/postgresql/data \
  infortributos/postgres:17.7
```

Verificar:

```bash
docker ps | grep fiscalia-postgres
```

### 4.7. Levantar la API

```bash
docker run -d --name fiscalia-api -p 8001:8000 \
  --env-file .env \
  -e POSTGRES_HOST=172.17.0.1 \
  -e POSTGRES_PORT=5433 \
  -e POSTGRES_DB=fiscalia \
  -e POSTGRES_USER=admin \
  -e POSTGRES_PASSWORD=A \
  infortributos/fiscalia-api:latest
```

### 4.8. Verificar que funciona

```bash
# Ver contenedores activos
docker ps

# Healthcheck
curl http://localhost:8001/api/v1/health

# Logs de la API
docker logs fiscalia-api

# Logs de PostgreSQL
docker logs fiscalia-postgres
```

### 4.9. Push a Docker Hub (para deploy futuro)

```bash
docker push infortributos/fiscalia-api:latest
```

## 5. Comandos Útiles

| Acción | Comando |
|---|---|
| Ver contenedores activos | `docker ps` |
| Ver todos los contenedores | `docker ps -a` |
| Logs de la API | `docker logs fiscalia-api` |
| Logs en tiempo real | `docker logs -f fiscalia-api` |
| Detener API | `docker stop fiscalia-api` |
| Eliminar API | `docker rm fiscalia-api` |
| Detener PostgreSQL | `docker stop fiscalia-postgres` |
| Eliminar PostgreSQL y datos | `docker rm -v fiscalia-postgres` |
| Ver redes | `docker network ls` |
| Ver volúmenes | `docker volume ls` |
| Ver imágenes | `docker images` |
| Limpiar contenedores detenidos | `docker container prune` |

## 6. Conexión desde DBeaver / Cliente Externo

| Campo | Valor |
|---|---|
| Host | `99.0.5.213` |
| Port | `5433` |
| Database | `fiscalia` |
| User | `admin` |
| Password | `A` |

## 7. Actualización (Rolling)

```bash
# Bajar cambios
cd /DATOS01/docker/docker01/fiscalia-ia
git fetch origin
git reset --hard origin/main

# Reconstruir imagen
DOCKER_BUILDKIT=0 docker build --no-cache -t infortributos/fiscalia-api:latest .

# Detener y reemplazar API
docker stop fiscalia-api
docker rm fiscalia-api

# Levar la nueva versión
docker run -d --name fiscalia-api -p 8001:8000 \
  --env-file .env \
  -e POSTGRES_HOST=172.17.0.1 \
  -e POSTGRES_PORT=5433 \
  infortributos/fiscalia-api:latest
```

La base de datos **no se pierde** porque el volumen `pgdata` persiste entre actualizaciones.

## 8. Notas sobre OPA (Open Policy Agent)

Este servidor tiene un plugin OPA que controla qué imágenes y operaciones están permitidas:

- **Imágenes permitidas**: `infortributos/*` y `python:3.14-slim`
- **Operaciones bloqueadas**: `docker compose up` con servicios nuevos, contenedores sin entrypoint shell
- **Solución**: Usar `docker run` para crear los contenedores individualmente y mantener las imágenes bajo el namespace `infortributos/`
