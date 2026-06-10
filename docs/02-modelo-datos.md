# Modelo de Datos — FiscalIA

> **Nota:** Estas tablas son responsabilidad del equipo APEX/PL-SQL. El microservicio las lee y escribe exclusivamente a través de los PL/SQL packages definidos en `docs/03-contrato-plsql.md`.

## 1. Convenciones

- Prefijo: `FISCAL_`
- Esquema: Taxation Smart Valledupar
- Motor: Oracle Database 19c+
- Tipos de datos Oracle

## 2. Tablas

### 2.1. FISCAL_CAMPANAS

Define cada campaña de fiscalización lanzada.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | NUMBER PK | Identificador único |
| `nombre` | VARCHAR2(200) | Nombre de la campaña |
| `periodo_ini` | DATE | Inicio del período fiscalizable |
| `periodo_fin` | DATE | Fin del período fiscalizable |
| `sector_ciiu` | VARCHAR2(10) | CIIU filtrado (opcional) |
| `estado` | VARCHAR2(20) | ACTIVA, CERRADA, EN_PROCESO |
| `config_json` | CLOB | Configuración adicional en JSON |
| `fecha_crea` | DATE | Fecha de creación |
| `usuario_id` | NUMBER | Usuario que la creó |

### 2.2. FISCAL_EXPEDIENTES

Expediente electrónico por contribuyente en proceso de fiscalización.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | NUMBER PK | Identificador único |
| `campana_id` | NUMBER FK | Referencia a FISCAL_CAMPANAS |
| `nit` | VARCHAR2(20) | NIT del contribuyente |
| `razon_social` | VARCHAR2(300) | Razón social |
| `numero_exp` | VARCHAR2(30) UNIQUE | Número único de expediente |
| `estado` | VARCHAR2(30) | ABIERTO, EN_ANALISIS, CERRADO |
| `funcionario_id` | NUMBER | ID del fiscalizador asignado |
| `fecha_apertura` | DATE | Fecha de apertura |

### 2.3. FISCAL_CRUCES

Registro de cada cruce de información ejecutado (AGT-01).

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | NUMBER PK | Identificador único |
| `expediente_id` | NUMBER FK | Referencia a FISCAL_EXPEDIENTES |
| `fuente` | VARCHAR2(30) | Origen del cruce (EXOGENA, DIAN, RUES) |
| `fecha_consulta` | TIMESTAMP | Momento de la consulta |
| `resultado_json` | CLOB | Resultado completo del cruce |
| `score_aporte` | NUMBER(5,2) | Puntaje que aporta al SRF |
| `usuario_audit` | VARCHAR2(50) | Usuario de auditoría |

### 2.4. FISCAL_SCORE_RIESGO

Score de Riesgo Fiscal (SRF) por contribuyente.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | NUMBER PK | Identificador único |
| `expediente_id` | NUMBER FK | Referencia a FISCAL_EXPEDIENTES |
| `srf_total` | NUMBER(5,2) | Score total 0-100 |
| `comp_exogena` | NUMBER(5,2) | Componente exógena (peso 35%) |
| `comp_tarifa` | NUMBER(5,2) | Componente tarifa CIIU (peso 25%) |
| `comp_omision` | NUMBER(5,2) | Componente omisión (peso 20%) |
| `comp_rues` | NUMBER(5,2) | Componente RUES (peso 20%) |
| `explicacion_clob` | CLOB | Explicación generada por IA |
| `fecha_calculo` | DATE | Fecha del cálculo |

### 2.5. FISCAL_OMISOS

Omisos detectados (AGT-02).

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | NUMBER PK | Identificador único |
| `campana_id` | NUMBER FK | Referencia a FISCAL_CAMPANAS |
| `fuente_deteccion` | VARCHAR2(30) | RUES, HISTORICO, EXOGENA |
| `nit` | VARCHAR2(20) | NIT del omiso |
| `razon_social` | VARCHAR2(300) | Razón social |
| `actividad_ciiu` | VARCHAR2(10) | CIIU principal |
| `evidencia_json` | CLOB | Evidencia estructurada |
| `estado` | VARCHAR2(20) | PENDIENTE, CONFIRMADO, DESCARTADO |
| `funcionario_id` | NUMBER | Fiscalizador asignado |
| `brecha_estimada` | NUMBER(18,2) | Brecha fiscal estimada en COP |

### 2.6. FISCAL_INCONSISTENCIAS

Inconsistencias detectadas (AGT-03).

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | NUMBER PK | Identificador único |
| `expediente_id` | NUMBER FK | Referencia a FISCAL_EXPEDIENTES |
| `declaracion_id` | NUMBER | ID de la declaración ICA asociada |
| `tipo_inc` | VARCHAR2(50) | Tipo: SUBREGISTRO, TARIFA, PERIODO, EXENCION, BASE_CERO |
| `descripcion` | CLOB | Descripción de la inconsistencia |
| `valor_declarado` | NUMBER(18,2) | Valor declarado en ICA |
| `valor_referencia` | NUMBER(18,2) | Valor de referencia (exógena, ley) |
| `diferencia` | NUMBER(18,2) | Diferencia en COP |
| `fuente_ref` | VARCHAR2(100) | Fuente del valor de referencia |
| `estado_hitl` | VARCHAR2(20) | PENDIENTE, CONFIRMADO, DESCARTADO |
| `analisis_ia` | CLOB | Análisis generado por IA |

### 2.7. FISCAL_ANALISIS_IA

Resultados del microservicio y respuestas del LLM. **Única tabla que el microservicio escribe directamente.**

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | NUMBER PK | Identificador único |
| `expediente_id` | NUMBER | FK a FISCAL_EXPEDIENTES (nullable en análisis sin expediente) |
| `tipo_analisis` | VARCHAR2(30) | COMPLETO, SRF |
| `prompt_enviado` | CLOB | Prompt enviado al LLM |
| `respuesta_ia` | CLOB | Respuesta completa del LLM |
| `tokens_entrada` | NUMBER | Tokens consumidos en el prompt |
| `tokens_salida` | NUMBER | Tokens generados en la respuesta |
| `costo_estimado` | NUMBER(10,4) | Costo estimado en USD |
| `fecha_analisis` | TIMESTAMP | Fecha del análisis |
| `cache_hit` | NUMBER(1) | 1 si fue servido de caché |

### 2.8. FISCAL_HITL_LOG

Log inmutable de decisiones Human-in-the-Loop.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | NUMBER PK | Identificador único |
| `expediente_id` | NUMBER FK | Referencia a FISCAL_EXPEDIENTES |
| `agente_origen` | VARCHAR2(20) | AGT-01, AGT-02, AGT-03 |
| `decision_ia` | VARCHAR2(100) | Decisión sugerida por la IA |
| `accion_humano` | VARCHAR2(100) | Decisión final del funcionario |
| `usuario_id` | NUMBER | ID del funcionario |
| `timestamp_op` | TIMESTAMP | Momento de la decisión |
| `justificacion` | VARCHAR2(500) | Justificación del funcionario |

### 2.9. FISCAL_AUDIT_LOG

Log de auditoría de todas las operaciones.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | NUMBER PK | Identificador único |
| `usuario` | VARCHAR2(50) | Usuario que ejecutó la operación |
| `fecha_ope` | TIMESTAMP | Fecha de la operación |
| `tipo_accion` | VARCHAR2(50) | Tipo: ANALISIS, CLASIFICACION, EXPORTACION |
| `nit_afectado` | VARCHAR2(20) | NIT del contribuyente afectado |
| `ip_origen` | VARCHAR2(50) | IP desde donde se ejecutó |
| `tabla_afectada` | VARCHAR2(50) | Tabla modificada |
| `descripcion` | VARCHAR2(500) | Descripción de la operación |

### 2.10. FISCAL_PESOS

Parámetros configurables del módulo.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | NUMBER PK | Identificador único |
| `parametro` | VARCHAR2(100) UNIQUE | Nombre del parámetro |
| `valor` | NUMBER(10,4) | Valor configurado |
| `descripcion` | VARCHAR2(300) | Descripción del parámetro |
| `fecha_modif` | DATE | Fecha de última modificación |
| `usuario_modif` | VARCHAR2(50) | Usuario que lo modificó |

## 3. Relaciones

```
FISCAL_CAMPANAS 1──N FISCAL_EXPEDIENTES
FISCAL_EXPEDIENTES 1──N FISCAL_CRUCES
FISCAL_EXPEDIENTES 1──1 FISCAL_SCORE_RIESGO
FISCAL_EXPEDIENTES 1──N FISCAL_INCONSISTENCIAS
FISCAL_EXPEDIENTES 1──N FISCAL_HITL_LOG
FISCAL_CAMPANAS 1──N FISCAL_OMISOS
```

## 4. DDL

Ver archivo: `db/migrations/001_tablas_fiscales.sql`
