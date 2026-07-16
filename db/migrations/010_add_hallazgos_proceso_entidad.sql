-- Agregar FK a procesos y entidades en hallazgos_fiscales
-- ON DELETE SET NULL: si se borra el proceso, el hallazgo sobrevive

ALTER TABLE hallazgos_fiscales
  ADD COLUMN proceso_id UUID REFERENCES procesos(id) ON DELETE SET NULL,
  ADD COLUMN entidad_id UUID REFERENCES entidades_fiscalizadoras(id) ON DELETE SET NULL;

CREATE INDEX idx_hallazgos_proceso ON hallazgos_fiscales(proceso_id);
CREATE INDEX idx_hallazgos_entidad ON hallazgos_fiscales(entidad_id);
