# Spec: Adaptar SRF y orquestador

## Behaviors — crosscheck_service.py

| ID | Given | When | Then |
|----|-------|------|------|
| B01 | Item con tipo OMISO_CONOCIDO, sin declaraciones | `clasificar_por_datos()` | Retorna "OMISO_CONOCIDO" |
| B02 | Item con tipo OMISO_DESCONOCIDO | `clasificar_por_datos()` | Retorna "OMISO_DESCONOCIDO" |
| B03 | Item con tipo INEXACTO_CIIU, tarifa_dian > tarifa_declarada | `extraer_inconsistencias()` | Genera inconsistencia TARIFA_INCORRECTA con los dos CIIU |
| B04 | Item con tipo INEXACTO_RETENCIONES, dif > 5% | `extraer_inconsistencias()` | Genera inconsistencia RETENCIONES_INCONSISTENTES |
| B05 | Item con tipo OMISO_DESCONOCIDO | `calcular_srf()` | Score alto (omision total + sin registro) |
| B06 | Item con tipo INEXACTO_CIIU | `calcular_srf()` | Componente CIIU con peso 25, tarifa DIAN vs declarada |
| B07 | Item con tipo INEXACTO_RETENCIONES | `calcular_srf()` | Componente retenciones con peso 20 |

## Behaviors — orquestar_proceso.py

| ID | Given | When | Then |
|----|-------|------|------|
| B10 | proceso creado con criteria.periodo="2023" | `ejecutar()` | Usa periodo="2023" en obtener_datos_fiscales |
| B11 | NIT clasificado como OMISO_CONOCIDO | `ejecutar()` | Procesa como omiso (mismo flujo que OMISO) |
| B12 | NIT clasificado como INEXACTO_CIIU | `ejecutar()` | Procesa como inexacto con datos CIIU |
| B13 | proceso con periodo omitido | `ejecutar()` | Usa default "2024" |

## Edge Cases

| ID | Scenario | Expected Behavior |
|----|----------|-------------------|
| E01 | Item sin campo `tipo` | Fallback a logica antigua (OMISO/INEXACTO) |
| E02 | INEXACTO_RETENCIONES sin diferencia_pct | No genera inconsistencia |
