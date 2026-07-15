-- Fix: agregar proceso_id a proceso_detalle_errores para filtrar por proceso
-- Bug: la tabla no tenia proceso_id, causando fuga de datos entre procesos

ALTER TABLE proceso_detalle_errores ADD COLUMN proceso_id UUID;

-- Backfill proceso_id desde proceso_detalle (seguro aunque haya 0 filas)
UPDATE proceso_detalle_errores e
SET proceso_id = d.proceso_id
FROM proceso_detalle d
WHERE e.detalle_id = d.id;

ALTER TABLE proceso_detalle_errores ALTER COLUMN proceso_id SET NOT NULL;
ALTER TABLE proceso_detalle_errores ADD CONSTRAINT fk_proceso_detalle_errores_proceso
    FOREIGN KEY (proceso_id) REFERENCES procesos(id);

CREATE INDEX idx_detalle_errores_proceso ON proceso_detalle_errores(proceso_id);

-- Eliminar indice redundante en clientes.nit (UNIQUE ya crea uno)
DROP INDEX IF EXISTS idx_clientes_nit;
