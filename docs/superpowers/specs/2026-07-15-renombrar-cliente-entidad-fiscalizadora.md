# Design: Renombrar "cliente" → "entidad_fiscalizadora"

## Contexto

El nombre actual cliente en la tabla y código genera confusión. Los usuarios creen que el "cliente" es el contribuyente que se analiza para fiscalización, cuando en realidad es la **entidad que solicita el análisis** (municipio como Valledupar, Cartagena, Barranquilla).

Además, el router POST /proceso crea clientes automáticamente si no existen, cuando las entidades deben estar pre-registradas.

## Decisión

- **Renombrar** tabla clientes → entidades_fiscalizadoras
- **Renombrar** todas las funciones, variables y schemas relacionadas
- **Agregar** endpoint POST /entidad_fiscalizadora para crear entidades
- **Modificar** POST /proceso para rechazar si la entidad no existe
- **Eliminar** creación automática de entidades en el router de proceso

## Alcance

### DB + Migración

**Tabla renombrada:**
`sql
ALTER TABLE procesos DROP CONSTRAINT IF EXISTS procesos_cliente_id_fkey;
ALTER TABLE clientes RENAME TO entidades_fiscalizadoras;
ALTER TABLE procesos RENAME COLUMN cliente_id TO entidad_id;
ALTER TABLE procesos ADD CONSTRAINT procesos_entidad_id_fkey 
  FOREIGN KEY (entidad_id) REFERENCES entidades_fiscalizadoras(id);
DROP INDEX IF EXISTS idx_procesos_cliente;
CREATE INDEX idx_procesos_entidad ON procesos(entidad_id);
`

**Nuevos comentarios:**
`sql
COMMENT ON TABLE entidades_fiscalizadoras IS 
  'Entidades fiscalizadoras (municipios, departamentos) que solicitan análisis del ICA. NO son los contribuyentes analizados.';
COMMENT ON COLUMN entidades_fiscalizadoras.nit IS 
  'NIT de la entidad fiscalizadora. Único.';
COMMENT ON COLUMN entidades_fiscalizadoras.razon_social IS 
  'Nombre oficial de la entidad.';
`

### Código (functions + variables)

**Funciones renombradas en queries.py:**

| Antes | Después |
|---|---|
| crear_cliente(nit, razon_social, email) | crear_entidad(nit, nombre, email) |
| obtener_cliente_por_nit(nit) | obtener_entidad_por_nit(nit) |
| obtener_cliente_por_id(cliente_id) | obtener_entidad_por_id(entidad_id) |
| desactivar_cliente(cliente_id) | desactivar_entidad(entidad_id) |
| reactivar_cliente(cliente_id) | reactivar_entidad(entidad_id) |

**Port ABC en proceso_repo.py:** Mismos cambios en las firmas.

**Repo en repositorio_proceso.py:** Delega a las nuevas funciones de queries.

**Variables renombradas:**
- cliente_id → entidad_id
- cliente_nit → entidad_nit (en schemas y router)
- req.cliente_nit → req.entidad_nit

**Error renombrado en errors.py:**
- ClienteNoEncontradoError → EntidadNoEncontradoError

### Routers + Schemas

**Router proceso.py — Cambio en POST /proceso:**
`python
@router.post("/proceso", status_code=201, response_model=ProcesoResponse)
async def crear_proceso(req: ProcesoRequest):
    entidad = await repo.obtener_entidad_por_nit(req.entidad_nit)
    if not entidad:
        raise EntidadNoEncontradoError(req.entidad_nit)
    
    criteria = {
        "vigencia_ini": req.vigencia_ini,
        # ... mismos campos ...
    }
    
    existing = await repo.obtener_proceso_por_criteria(entidad["id"], criteria)
    # ... resto igual ...
    
    proceso_id = await repo.crear_proceso(entidad["id"], req.nombre, criteria)
`

**Nuevo router entidad.py — CRUD de entidades:**
`python
@router.post("/entidad_fiscalizadora", status_code=201)
async def crear_entidad(req: EntidadRequest):
    existing = await repo.obtener_entidad_por_nit(req.nit)
    if existing:
        raise FiscalIAError("Ya existe una entidad con ese NIT")
    entidad_id = await repo.crear_entidad(req.nit, req.nombre, req.email)
    return {"id": entidad_id, "nit": req.nit, "nombre": req.nombre}

@router.get("/entidad_fiscalizadora/{nit}")
async def obtener_entidad(nit: str):
    entidad = await repo.obtener_entidad_por_nit(nit)
    if not entidad:
        raise EntidadNoEncontradoError(nit)
    return entidad

@router.get("/entidad_fiscalizadoras")
async def listar_entidades(page=1, page_size=20):
    # Listar entidades activas
`

**Schema ProcesoRequest:**
`python
class ProcesoRequest(BaseModel):
    entidad_nit: str = Field(..., description="NIT de la entidad fiscalizadora (municipio/entidad)")
    nombre: str = Field(..., description="Nombre del proceso")
    # ... resto igual ...
`

**Schema ProcesoResponse:**
`python
class ProcesoResponse(BaseModel):
    entidad_nit: str  # antes: cliente_nit
    # ... resto igual ...
`

**Schema nuevo EntidadRequest:**
`python
class EntidadRequest(BaseModel):
    nit: str = Field(..., description="NIT de la entidad fiscalizadora")
    nombre: str = Field(..., description="Nombre oficial de la entidad")
    email: str | None = Field(None, description="Correo de contacto (opcional)")
`

### Tests (~55 referencias)

- tests/unit/test_queries.py: Renombrar funciones de test
- tests/unit/test_proceso_router.py: Mocks y assertions con entidad_nit
- tests/unit/test_domain_errors.py: test_cliente_no_encontrado → test_entidad_no_encontrado
- tests/functional/conftest.py: cliente_nit → entidad_nit en fixtures
- tests/functional/test_proceso.py: Actualizar assertions
- tests/integration/test_proceso_integration.py: Actualizar mocks y assertions
- tests/e2e/conftest.py, tests/e2e/test_estado_resultados_errores.py
- tests/stress/locustfile.py, tests/stress/locustfile_stress.py

### Docs

- AGENTS.md: Actualizar descripción de "cliente" → "entidad fiscalizadora"
- docs/02-modelo-datos.md: Si existe, actualizar

### main.py

`python
from routers.entidad import router as entidad_router
app.include_router(entidad_router, prefix="/api/v1", tags=["entidad"])
`

## Endpoint Existente Afectado

| Endpoint | Cambio |
|---|---|
| POST /proceso | Rechaza 404 si entidad_nit no existe (antes creaba automaticamente) |
| GET /proceso/{id}/status | Retorna entidad_nit en vez de cliente_nit |

## Orden de Ejecución

1. Migracion SQL
2. Queries + Port + Repo (renombrar funciones)
3. Errors (renombrar error)
4. Schemas (renombrar campos)
5. Router proceso (cambiar logica)
6. Nuevo router entidad
7. main.py (registrar router)
8. Tests
9. Docs (AGENTS.md)
10. Lint + verify
