# Spec: Alinear FiscalIA con metodologia real de candidatos ICA

## Behaviors

### Omisos Conocidos (nueva query SQL)

| ID | Given | When | Then |
|----|-------|------|------|
| B01 | Periodo fiscal (ej: "2024"), regimen | Se llama `obtener_omisos_conocidos(client, vigencia, periodo, page_size)` | Ejecuta query que cruza SI_I_SUJETOS_IMPUESTO + SI_I_PERSONAS + SI_C_SUJETOS y filtra contribuyentes sin declaracion valida en GI_G_DECLARACIONES para ese periodo |
| B02 | Contribuyente con inscripcion ICA cancelada antes del periodo | Se ejecuta la query | No aparece en resultados |
| B03 | Contribuyente con fecha inicio actividades posterior al periodo | Se ejecuta la query | No aparece en resultados |
| B04 | Contribuyente con declaracion valida en GI_G_DECLARACIONES | Se ejecuta la query | No aparece en resultados |
| B05 | Contribuyente con expediente FI_G_FISCALIZACION_EXPDNTE existente (programa Omisos) | Se ejecuta la query | No aparece en resultados (exclusion) |
| B06 | Contribuyente sin declaracion, sin expediente previo | Se ejecuta la query | Aparece como OMISO_CONOCIDO con datos: NIT, razon_social, CIIU, direccion, fecha_inicio, periodos_omisos |

### Omisos Desconocidos (nueva funcion)

| ID | Given | When | Then |
|----|-------|------|------|
| B10 | Vigencia fiscal | Se llama `obtener_omisos_desconocidos(client, vigencia, page_size)` | Cruza TEMP_RQ_DIAN + SI_C_SUJETOS; NITs en DIAN que NO existen en SI_C_SUJETOS ni SI_I_SUJETOS_IMPUESTO se marcan OMISO_DESCONOCIDO |
| B11 | NIT aparece en DIAN y en SI_C_SUJETOS pero sin declaracion | Se ejecuta | Se reclasifica como OMISO_CONOCIDO (no desconocido) |
| B12 | NIT en DIAN ya tiene expediente FI_* de omisos | Se ejecuta | Se excluye (no duplicado) |
| B13 | NIT en GI_G_EXOGENA_RETENCIONES no existe en SI_C_SUJETOS | Se ejecuta | Se marca OMISO_DESCONOCIDO (fuente: exogena) |
| B14 | Omiso desconocido detectado por DIAN y exogena simultaneamente | Se ejecuta | Se consolida en un solo registro, fuente="DIAN+EXOGENA" |

### Inexactos CIIU (nueva funcion)

| ID | Given | When | Then |
|----|-------|------|------|
| B20 | Contribuyente con declaracion valida | Se llama `obtener_inexactos_ciiu(client, periodo, page_size)` | Cruza CIIU en GI_G_DECLARACIONES_DETALLE vs CIIU en TEMP_RQ_DIAN; si son diferentes Y tarifa DIAN > tarifa declarada, se marca INEXACTO_CIIU |
| B21 | CIIU DIAN igual al CIIU declarado | Se evalua | No se genera candidato |
| B22 | Tarifa DIAN <= tarifa declarada | Se evalua | No se genera candidato (solo alerta si la DIAN reporta tarifa MAYOR) |
| B23 | Ya existe expediente FI_* de inexactos para ese NIT y periodo | Se evalua | Se excluye |
| B24 | Multiples atributos CIIU en la declaracion (actividades secundarias) | Se evalua | Se compara la actividad PRINCIPAL de la DIAN contra TODAS las actividades declaradas; si al menos una coincide, no hay alerta |

### Inexactos Retenciones (nueva funcion)

| ID | Given | When | Then |
|----|-------|------|------|
| B30 | Contribuyente con declaracion valida y datos en exogena | Se llama `obtener_inexactos_retenciones(client, periodo, page_size)` | Compara retenciones declaradas (GI_G_DECLARACIONES_DETALLE, atributos 717/718/5035/5036) vs retenciones en GI_G_EXOGENA_RETENCIONES; si diferencia > umbral, se marca INEXACTO_RETENCIONES |
| B31 | Diferencia de retenciones menor al umbral (ej: <5%) | Se evalua | No se genera candidato |
| B32 | Sin datos en exogena para ese NIT | Se evalua | No se genera candidato |
| B33 | Ya existe expediente FI_* de inexactos para ese NIT y periodo | Se evalua | Se excluye |

### Classify (expandido)

| ID | Given | When | Then |
|----|-------|------|------|
| B40 | Item con `tipo="OMISO_CONOCIDO"` | `clasificar_candidato(item)` | Retorna ("OMISO_CONOCIDO", detalle) |
| B41 | Item con `tipo="OMISO_DESCONOCIDO"` | `clasificar_candidato(item)` | Retorna ("OMISO_DESCONOCIDO", detalle) |
| B42 | Item con `tipo="INEXACTO_CIIU"` | `clasificar_candidato(item)` | Retorna ("INEXACTO", detalle con razon CIIU) |
| B43 | Item con `tipo="INEXACTO_RETENCIONES"` | `clasificar_candidato(item)` | Retorna ("INEXACTO", detalle con razon retenciones) |
| B44 | Item sin tipo (legacy) | `clasificar_candidato(item)` | Usa logica antigua de `es_candidato`, `score_peso`, `es_omiso` como fallback |

## Edge Cases

| ID | Scenario | Expected Behavior |
|----|----------|-------------------|
| E01 | `obtener_omisos_conocidos` con 0 resultados | Retorna generator vacio |
| E02 | DIAN sin datos para la vigencia (tabla TEMP_RQ_DIAN vacia) | `obtener_omisos_desconocidos` retorna generator vacio |
| E03 | Exogena sin datos para la vigencia | `obtener_inexactos_retenciones` retorna generator vacio |
| E04 | Contribuyente con multiples declaraciones en el periodo (correcciones) | Solo se considera la ultima declaracion valida no anulada |
| E05 | CIIU no encontrado en tabla de tarifas (TARIFAS_CIIU provisional) | Se usa tarifa=0, no se genera alerta de inexactitud CIIU |
| E06 | Umbral de diferencia en retenciones no configurado | Default: 5% de tolerancia |

## Constraints

- Todas las queries se ejecutan via `EXECUTE_SQL` del Oracle MCP Server
- El filtro de exclusion FI_* se implementa como subconsultas SQL (responsabilidad de Oracle, no de Python)
- Backward compatibility: `obtener_datos_fiscales()` mantiene su firma actual
- Los tipos de clasificacion nuevos se agregan sin eliminar los existentes
- Paginacion via `OFFSET/FETCH NEXT` (Oracle 12c+)
