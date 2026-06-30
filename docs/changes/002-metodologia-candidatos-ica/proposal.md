# Proposal: Alinear FiscalIA con metodologia real de candidatos ICA

## Intent

Adaptar las queries SQL, logica de clasificacion y exclusion de `pagination.py` y `classify.py` al esquema real de tablas Oracle del sistema Taxation Smart, segun el documento "Metodologia de Identificacion de Candidatos a Fiscalizacion ICA v1.0" (Valledupar). El codigo actual usa nombres de tablas genericos (`contribuyentes`, `declaraciones_ica`, `exogena_dian`, `rues`) que no corresponden al sistema real.

## Scope

- **In scope**:
  - **`pagination.py`**: Reemplazar las 4 queries SQL genericas con queries reales usando las tablas documentadas: `SI_C_SUJETOS`, `SI_I_SUJETOS_IMPUESTO`, `SI_I_PERSONAS`, `GI_G_DECLARACIONES`, `GI_G_DECLARACIONES_DETALLE`, `TEMP_RQ_DIAN`, `GI_G_EXOGENA_RETENCIONES`, `FI_G_CANDIDATOS`, `FI_G_CANDIDATOS_VIGENCIA`, `FI_G_FISCALIZACION_EXPDNTE`, `FI_G_FSCLZC_EXPDN_CNDD_VGNC`, `FI_D_PROGRAMAS`
  - **`classify.py`**: Expandir clasificacion de 3 tipos (OMISO/EXACTO/INEXACTO) a los tipos reales: OMISO_CONOCIDO, OMISO_DESCONOCIDO, INEXACTO_CIIU, INEXACTO_RETENCIONES, EXACTO
  - **`pagination.py`**: Agregar logica de exclusion por expediente existente (filtro FI_*)
  - **`pagination.py`**: Agregar funcion `obtener_omisos_desconocidos()` para cruce DIAN
  - **`pagination.py`**: Agregar funcion `obtener_inexactos_ciiu()` para cruce CIIU DIAN vs declarado
  - **`pagination.py`**: Agregar funcion `obtener_inexactos_retenciones()` para cruce exogena vs declarado
  - Tests de caracterizacion para todas las funciones nuevas/modificadas
- **Out of scope**:
  - Modificaciones a `crosscheck_service.py` (SRF) — se adapta en ciclo futuro
  - Modificaciones a `orquestar_proceso.py` — se adapta en ciclo futuro
  - Ingesta del archivo DIAN (carga a `TEMP_RQ_DIAN`) — es responsabilidad del sistema APEX
  - Parametrizacion del periodo (sigue hardcodeado "2024")
  - UI / APEX — este ciclo solo toca el microservicio Python

## Approach

1. **Reemplazar queries SQL**: Cada query actual en `pagination.py` se reemplaza con la version que usa nombres reales de tablas y columnas Oracle.
2. **Funciones nuevas**: Se agregan funciones asincronas `obtener_omisos_desconocidos()`, `obtener_inexactos_ciiu()`, `obtener_inexactos_retenciones()`.
3. **Exclusion**: La funcion `paginar_contribuyentes()` incorpora el filtro anti-duplicados via las tablas FI_*.
4. **Clasificacion expandida**: `classify.py` soporta los 5 tipos de resultado.
5. **TDD estricto**: Tests RED antes de cada implementacion GREEN.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Nombres de columnas incorrectos en queries | Alta | Alto | Validar contra el documento; documentar supuestos en comentarios SQL |
| Performance con JOINs complejos (FI_*) | Media | Medio | Usar subconsultas con EXISTS en lugar de JOINs cuando sea posible |
| Logica de exclusion muy acoplada a APEX | Media | Medio | Implementar como filtro en SQL, manteniendo la responsabilidad en el MCP Server (Oracle) |
| Romper tests existentes de `pagination.py` y `classify.py` | Alta | Bajo | Actualizar tests existentes para reflejar la nueva estructura |

## Affected Components

- `infrastructure/mcp/pagination.py` — reescritura de queries + funciones nuevas
- `infrastructure/mcp/classify.py` — expansion de clasificacion
- `tests/unit/test_pagination.py` — nuevos tests + actualizar existentes
- `tests/unit/test_classify.py` — nuevos tests + actualizar existentes
- `tests/unit/test_mcp_client.py` — actualizar si es necesario
- `tests/unit/test_orchestrator.py` — actualizar mocks si cambian firmas
- `MEMORY/CONTEXT.md` — documentar mapeo de tablas
