-- =============================================
-- 008: Comentarios de schema para documentacion
-- =============================================
-- Idempotente: COMMENT ON reemplaza comentarios existentes.
-- NOTA: Sin tildes para evitar problemas de encoding en psql.

-- ─── clientes ───

COMMENT ON TABLE clientes IS
  'Clientes (contribuyentes/empresas) que contratan procesos de fiscalizacion del ICA. Cada cliente se identifica por su NIT.';

COMMENT ON COLUMN clientes.id IS 'Identificador unico UUID del cliente.';
COMMENT ON COLUMN clientes.nit IS 'Numero de Identificacion Tributaria (NIT) del contribuyente. Unico por cliente.';
COMMENT ON COLUMN clientes.razon_social IS 'Razon social o nombre comercial registrado ante la DIAN.';
COMMENT ON COLUMN clientes.email IS 'Correo electronico de contacto del cliente (opcional).';
COMMENT ON COLUMN clientes.activo IS 'Estado del cliente: TRUE = activo, FALSE = desactivado (soft-delete).';
COMMENT ON COLUMN clientes.created_at IS 'Fecha y hora de creacion del registro.';

-- ─── procesos ───

COMMENT ON TABLE procesos IS
  'Procesos de fiscalizacion del ICA. Cada proceso representa una campana de analisis de contribuyentes para un cliente y periodo especifico.';

COMMENT ON COLUMN procesos.id IS 'Identificador unico UUID del proceso de fiscalizacion.';
COMMENT ON COLUMN procesos.cliente_id IS 'FK > clientes.id. Cliente propietario del proceso.';
COMMENT ON COLUMN procesos.nombre IS 'Nombre descriptivo del proceso (ej: "Campana ICA 2024 Valledupar").';
COMMENT ON COLUMN procesos.estado IS 'Estado del proceso: PENDIENTE > PREFILTRANDO > PREFILTRADO_COMPLETADO > EN_PROCESO > COMPLETADO | ERROR.';
COMMENT ON COLUMN procesos.criteria IS 'Criterios de busqueda en JSON (periodo, actividad economica, vigencias, regimen).';
COMMENT ON COLUMN procesos.total_nits IS 'Total de NITs unicos encontrados en la fase de descubrimiento.';
COMMENT ON COLUMN procesos.candidatos IS 'Total de candidatos a fiscalizacion (OMISOS + INEXACTOS).';
COMMENT ON COLUMN procesos.omisos IS 'Cantidad de contribuyentes clasificados como OMISO (sin declaraciones ICA).';
COMMENT ON COLUMN procesos.exactos IS 'Cantidad de contribuyentes clasificados como EXACTO (declaraciones correctas).';
COMMENT ON COLUMN procesos.inexactos IS 'Cantidad de contribuyentes clasificados como INEXACTO (declaraciones con inconsistencias).';
COMMENT ON COLUMN procesos.intentos_total IS 'Numero total de intentos de ejecucion del proceso.';
COMMENT ON COLUMN procesos.created_at IS 'Fecha y hora de creacion del proceso.';

-- ─── proceso_intentos ───

COMMENT ON TABLE proceso_intentos IS
  'Intentos de ejecucion de un proceso. Cada intento representa una corrida completa del pipeline (pre-filtro + analisis IA). Permite reintentos automaticos.';

COMMENT ON COLUMN proceso_intentos.id IS 'Identificador unico SERIAL del intento.';
COMMENT ON COLUMN proceso_intentos.proceso_id IS 'FK > procesos.id. Proceso padre al que pertenece este intento.';
COMMENT ON COLUMN proceso_intentos.numero_intento IS 'Numero secuencial del intento (1, 2, 3...).';
COMMENT ON COLUMN proceso_intentos.estado IS 'Estado del intento: PREFILTRANDO, PREFILTRADO_COMPLETADO, EN_PROCESO, COMPLETADO, ERROR.';
COMMENT ON COLUMN proceso_intentos.procesados IS 'Cantidad de NITs procesados exitosamente en este intento.';
COMMENT ON COLUMN proceso_intentos.errores_count IS 'Cantidad de errores ocurridos durante este intento.';
COMMENT ON COLUMN proceso_intentos.error_resumen IS 'Resumen del error principal si el intento termino en ERROR.';
COMMENT ON COLUMN proceso_intentos.started_at IS 'Fecha y hora de inicio del intento.';
COMMENT ON COLUMN proceso_intentos.completed_at IS 'Fecha y hora de finalizacion del intento (NULL si esta en proceso).';

-- ─── proceso_detalle ───

COMMENT ON TABLE proceso_detalle IS
  'Detalle de cada contribuyente analizado dentro de un proceso. Contiene clasificacion, scores MCP y SRF, hallazgos, y la explicacion generada por IA.';

COMMENT ON COLUMN proceso_detalle.id IS 'Identificador unico SERIAL del registro de detalle.';
COMMENT ON COLUMN proceso_detalle.proceso_id IS 'FK > procesos.id. Proceso al que pertenece este contribuyente.';
COMMENT ON COLUMN proceso_detalle.intento_id IS 'FK > proceso_intentos.id. Intento que genero este registro.';
COMMENT ON COLUMN proceso_detalle.nit IS 'NIT del contribuyente analizado.';
COMMENT ON COLUMN proceso_detalle.razon_social IS 'Razon social del contribuyente (desde Oracle o vacia).';
COMMENT ON COLUMN proceso_detalle.ciiu IS 'Codigo CIIU de la actividad economica declarada (ej: 4711, 4719).';
COMMENT ON COLUMN proceso_detalle.mcp_score IS 'Score de Cumplimiento Municipal calculado desde datos Oracle.';
COMMENT ON COLUMN proceso_detalle.es_candidato IS 'TRUE si es candidato (OMISO/INEXACTO), FALSE si es EXACTO.';
COMMENT ON COLUMN proceso_detalle.mcp_razon IS 'Justificacion textual del score MCP.';
COMMENT ON COLUMN proceso_detalle.clasificacion IS 'Clasificacion: OMISO_CONOCIDO, OMISO_DESCONOCIDO, INEXACTO_CIIU, INEXACTO_RETENCIONES, EXACTO.';
COMMENT ON COLUMN proceso_detalle.detalle_clasificacion IS 'Detalle adicional de la clasificacion.';
COMMENT ON COLUMN proceso_detalle.srf_total IS 'Score de Riesgo Fiscal total (0.0 a 1.0). Cruce de datos Oracle + reglas fiscales.';
COMMENT ON COLUMN proceso_detalle.nivel_riesgo IS 'Nivel de riesgo: BAJO, MEDIO, ALTO, CRITICO. Derivado del SRF.';
COMMENT ON COLUMN proceso_detalle.hallazgos IS 'Lista JSON de hallazgos: OMISION, INCONSISTENCIA, PATRON_TEMPORAL, COMPORTAMENTAL.';
COMMENT ON COLUMN proceso_detalle.explicacion_ia IS 'Explicacion en lenguaje natural generada por el LLM.';
COMMENT ON COLUMN proceso_detalle.tokens_entrada IS 'Tokens de entrada consumidos por el LLM para este NIT.';
COMMENT ON COLUMN proceso_detalle.tokens_salida IS 'Tokens de salida consumidos por el LLM para este NIT.';
COMMENT ON COLUMN proceso_detalle.costo_estimado IS 'Costo estimado en USD del consumo de tokens IA.';
COMMENT ON COLUMN proceso_detalle.pagina IS 'Pagina del descubrimiento Oracle (trazabilidad de paginacion).';
COMMENT ON COLUMN proceso_detalle.created_at IS 'Fecha y hora de creacion del registro.';

-- ─── proceso_errores ───

COMMENT ON TABLE proceso_errores IS
  'Errores a nivel de proceso completo. Fallas en descubrimiento (MCP/Oracle) o errores fatales del pipeline.';

COMMENT ON COLUMN proceso_errores.id IS 'Identificador unico SERIAL del error.';
COMMENT ON COLUMN proceso_errores.proceso_id IS 'FK > procesos.id. Proceso donde ocurrio el error.';
COMMENT ON COLUMN proceso_errores.intento_id IS 'FK > proceso_intentos.id. Intento especifico donde fallo.';
COMMENT ON COLUMN proceso_errores.capa IS 'Capa del sistema: MCP, ORACLE, LLM, POSTGRES, PROCESO.';
COMMENT ON COLUMN proceso_errores.codigo IS 'Codigo del error: CAMPANA_FAIL, MCP_TIMEOUT, MCP_ALL_FAIL, etc.';
COMMENT ON COLUMN proceso_errores.mensaje IS 'Mensaje descriptivo del error (exception message).';
COMMENT ON COLUMN proceso_errores.contexto IS 'Contexto adicional en JSON (NIT, datos parciales, SQL).';
COMMENT ON COLUMN proceso_errores.created_at IS 'Fecha y hora de registro del error.';

-- ─── proceso_detalle_errores ───

COMMENT ON TABLE proceso_detalle_errores IS
  'Errores a nivel de contribuyente (NIT). Fallas individuales durante el analisis IA de cada contribuyente.';

COMMENT ON COLUMN proceso_detalle_errores.id IS 'Identificador unico SERIAL del error de detalle.';
COMMENT ON COLUMN proceso_detalle_errores.detalle_id IS 'FK > proceso_detalle.id. Detalle del contribuyente que fallo.';
COMMENT ON COLUMN proceso_detalle_errores.proceso_id IS 'FK > procesos.id. Proceso (filtrado directo sin JOIN).';
COMMENT ON COLUMN proceso_detalle_errores.nit IS 'NIT del contribuyente donde ocurrio el error.';
COMMENT ON COLUMN proceso_detalle_errores.capa IS 'Capa del sistema: MCP, ORACLE, LLM, PROCESO.';
COMMENT ON COLUMN proceso_detalle_errores.codigo IS 'Codigo del error: ORCHESTRATION_FAIL, ANALISIS_FAIL, LLM_TIMEOUT.';
COMMENT ON COLUMN proceso_detalle_errores.mensaje IS 'Mensaje descriptivo del error.';
COMMENT ON COLUMN proceso_detalle_errores.contexto IS 'Contexto adicional en JSON (datos fiscales, stack trace).';
COMMENT ON COLUMN proceso_detalle_errores.created_at IS 'Fecha y hora de registro del error.';

-- ─── hallazgos_fiscales ───

COMMENT ON TABLE hallazgos_fiscales IS
  'Hallazgos fiscales detectados por el motor de reglas (R01-R10). Representan inconsistencias o incumplimientos especificos por contribuyente y periodo.';

COMMENT ON COLUMN hallazgos_fiscales.id IS 'Identificador unico UUID del hallazgo fiscal.';
COMMENT ON COLUMN hallazgos_fiscales.nit IS 'NIT del contribuyente asociado al hallazgo.';
COMMENT ON COLUMN hallazgos_fiscales.regla IS 'Codigo de la regla fiscal que detecto el hallazgo (R01-R10).';
COMMENT ON COLUMN hallazgos_fiscales.periodo IS 'Periodo fiscal del hallazgo (YYYY o YYYY-MM).';
COMMENT ON COLUMN hallazgos_fiscales.tipo_hallazgo IS 'Tipo: OMISION, INCONSISTENCIA_CIIU, INCONSISTENCIA_RETENCIONES, CAIDA_BSA, ANOMALIA_COMPORTAMENTAL.';
COMMENT ON COLUMN hallazgos_fiscales.fuerza_probatoria IS 'Nivel: ALTA, MEDIA, BAJA. Depende de la fuente y consistencia de los datos.';
COMMENT ON COLUMN hallazgos_fiscales.brecha_valor IS 'Diferencia monetaria estimada (COP) entre lo declarado y lo real.';
COMMENT ON COLUMN hallazgos_fiscales.impuesto_estimado IS 'Monto estimado del impuesto adeudado (COP).';
COMMENT ON COLUMN hallazgos_fiscales.score IS 'Score de confianza del hallazgo (0.00 a 1.00).';
COMMENT ON COLUMN hallazgos_fiscales.score_componentes IS 'Desglose JSON del score: regla, comportamiento, temporal, SRF.';
COMMENT ON COLUMN hallazgos_fiscales.ventana_limite IS 'Fecha limite para accion de fiscalizacion (prescripcion).';
COMMENT ON COLUMN hallazgos_fiscales.accionable IS 'TRUE si el hallazgo es accionable para cobro/fiscalizacion.';
COMMENT ON COLUMN hallazgos_fiscales.estado IS 'Estado: DETECTADO, EN_REVISION, CONFIRMADO, DESCARTADO, PRESCRITO.';
COMMENT ON COLUMN hallazgos_fiscales.resumen IS 'Resumen textual del hallazgo generado por IA.';
COMMENT ON COLUMN hallazgos_fiscales.metadata IS 'Metadatos JSON: calculos intermedios, datos crudos, config de reglas.';
COMMENT ON COLUMN hallazgos_fiscales.created_at IS 'Fecha y hora de creacion del hallazgo.';
COMMENT ON COLUMN hallazgos_fiscales.updated_at IS 'Fecha y hora de ultima actualizacion del hallazgo.';

-- ─── hallazgo_evidencias ───

COMMENT ON TABLE hallazgo_evidencias IS
  'Evidencias que soportan un hallazgo fiscal. Cada hallazgo puede tener multiples evidencias de diferentes fuentes (Oracle, DIAN, reglas, comportamiento).';

COMMENT ON COLUMN hallazgo_evidencias.id IS 'Identificador unico UUID de la evidencia.';
COMMENT ON COLUMN hallazgo_evidencias.hallazgo_id IS 'FK > hallazgos_fiscales.id (ON DELETE CASCADE). Hallazgo padre.';
COMMENT ON COLUMN hallazgo_evidencias.fuente IS 'Fuente: ORACLE, DIAN, MUNICIPAL, BEHAVIORAL, LLM, REGLA_FISCAL.';
COMMENT ON COLUMN hallazgo_evidencias.referencia_registro IS 'Referencia al registro fuente (ID de tabla, consulta SQL).';
COMMENT ON COLUMN hallazgo_evidencias.descripcion IS 'Descripcion legible de la evidencia encontrada.';
COMMENT ON COLUMN hallazgo_evidencias.snapshot IS 'Snapshot JSON del estado del dato al momento de la deteccion.';
COMMENT ON COLUMN hallazgo_evidencias.created_at IS 'Fecha y hora de creacion de la evidencia.';

-- ─── hallazgo_revisiones ───

COMMENT ON TABLE hallazgo_revisiones IS
  'Revisiones humanas de hallazgos fiscales. Registra las decisiones de los funcionarios (VALIDAR, DESCARTAR, PEDIR_INFO, ESCALAR).';

COMMENT ON COLUMN hallazgo_revisiones.id IS 'Identificador unico UUID de la revision.';
COMMENT ON COLUMN hallazgo_revisiones.hallazgo_id IS 'FK > hallazgos_fiscales.id (ON DELETE CASCADE). Hallazgo revisado.';
COMMENT ON COLUMN hallazgo_revisiones.funcionario_id IS 'Identificacion del funcionario que reviso.';
COMMENT ON COLUMN hallazgo_revisiones.decision IS 'Decision: VALIDAR, DESCARTAR, PEDIR_INFO, ESCALAR.';
COMMENT ON COLUMN hallazgo_revisiones.motivo IS 'Justificacion de la decision (texto libre).';
COMMENT ON COLUMN hallazgo_revisiones.created_at IS 'Fecha y hora de la revision.';

-- ─── hallazgo_revisiones_agente ───

COMMENT ON TABLE hallazgo_revisiones_agente IS
  'Revisiones automaticas de agentes IA sobre hallazgos fiscales. Trazabilidad completa de analisis automatizados y consumo de tokens.';

COMMENT ON COLUMN hallazgo_revisiones_agente.id IS 'Identificador unico UUID de la revision del agente.';
COMMENT ON COLUMN hallazgo_revisiones_agente.hallazgo_id IS 'FK > hallazgos_fiscales.id (ON DELETE CASCADE). Hallazgo revisado.';
COMMENT ON COLUMN hallazgo_revisiones_agente.agente IS 'Nombre/ID del agente IA: AGT-01, AGT-02, AGT-03, AGT-04, AGT-05.';
COMMENT ON COLUMN hallazgo_revisiones_agente.version IS 'Version del agente que ejecuto la revision.';
COMMENT ON COLUMN hallazgo_revisiones_agente.resultado IS 'Resultado JSON: analisis, recomendacion, nivel de confianza.';
COMMENT ON COLUMN hallazgo_revisiones_agente.modo_degradado IS 'TRUE si opero sin LLM completo (fallback o reglas simples).';
COMMENT ON COLUMN hallazgo_revisiones_agente.tokens_entrada IS 'Tokens de entrada consumidos en esta revision.';
COMMENT ON COLUMN hallazgo_revisiones_agente.tokens_salida IS 'Tokens de salida consumidos en esta revision.';
COMMENT ON COLUMN hallazgo_revisiones_agente.created_at IS 'Fecha y hora de la revision del agente.';
