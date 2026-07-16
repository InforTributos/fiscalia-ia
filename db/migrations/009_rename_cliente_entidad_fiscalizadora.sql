-- Renombrar tabla clientes → entidades_fiscalizadoras
-- Renombrar FK en procesos

ALTER TABLE procesos DROP CONSTRAINT IF EXISTS procesos_cliente_id_fkey;
ALTER TABLE procesos RENAME COLUMN cliente_id TO entidad_id;
ALTER TABLE clientes RENAME TO entidades_fiscalizadoras;
ALTER TABLE procesos ADD CONSTRAINT procesos_entidad_id_fkey
  FOREIGN KEY (entidad_id) REFERENCES entidades_fiscalizadoras(id);
DROP INDEX IF EXISTS idx_procesos_cliente;
CREATE INDEX idx_procesos_entidad ON procesos(entidad_id);

COMMENT ON TABLE entidades_fiscalizadoras IS
  'Entidades fiscalizadoras (municipios, departamentos) que solicitan analisis del ICA. NO son los contribuyentes analizados.';
COMMENT ON COLUMN entidades_fiscalizadoras.nit IS
  'NIT de la entidad fiscalizadora. Unico.';
COMMENT ON COLUMN entidades_fiscalizadoras.razon_social IS
  'Nombre oficial de la entidad.';
