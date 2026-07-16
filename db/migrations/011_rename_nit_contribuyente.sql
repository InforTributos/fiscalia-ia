-- Renombrar columnas nit a contribuyente_nit para claridad semantica
-- En tablas donde nit == CONTRIBUYENTE (no entidad fiscalizadora)

ALTER TABLE proceso_detalle RENAME COLUMN nit TO contribuyente_nit;
ALTER TABLE proceso_detalle_errores RENAME COLUMN nit TO contribuyente_nit;
ALTER TABLE hallazgos_fiscales RENAME COLUMN nit TO contribuyente_nit;

DROP INDEX IF EXISTS idx_proceso_detalle_nit;
CREATE INDEX idx_proceso_detalle_contribuyente ON proceso_detalle(contribuyente_nit);

DROP INDEX IF EXISTS idx_hallazgos_nit_periodo;
CREATE INDEX idx_hallazgos_contribuyente_periodo ON hallazgos_fiscales(contribuyente_nit, periodo);
