-- Pre-registrar entidades fiscalizadoras
-- Basado en configs de Harness/apex_infortributos/config/clientes/
-- NITs de fuentes oficiales (páginas municipales, SECOP, DIAN)

-- Limpiar registros inválidos previos
DELETE FROM entidades_fiscalizadoras WHERE nit IN ('audit', '800098911');

-- Asegurar Valledupar con datos correctos
INSERT INTO entidades_fiscalizadoras (nit, razon_social, activo)
VALUES ('800098911-8', 'Alcaldía Municipal de Valledupar', true)
ON CONFLICT (nit) DO UPDATE SET razon_social = EXCLUDED.razon_social;

-- Insertar todas las entidades (idempotente)
INSERT INTO entidades_fiscalizadoras (nit, razon_social, activo) VALUES
('890480184-4', 'Alcaldía Distrital de Cartagena de Indias', true),
('891780009-4', 'Alcaldía Distrital de Santa Marta', true),
('890501434-2', 'Alcaldía Municipal de San José de Cúcuta', true),
('800104062-6', 'Alcaldía Municipal de Sincelejo', true),
('892115007-2', 'Alcaldía Distrital de Riohacha', true),
('800028432-2', 'Alcaldía Municipal de Magangué', true),
('892280032-2', 'Alcaldía Municipal de Corozal', true),
('800075537-7', 'Alcaldía Municipal de San Carlos (Córdoba)', true),
('800096753-1', 'Alcaldía Municipal de Chinú', true),
('892280061',   'Alcaldía Municipal de Sucre (Sucre)', true),
('890106291-2', 'Alcaldía Municipal de Soledad', true),
('890201900-6', 'Alcaldía Municipal de Barrancabermeja', true),
('800096734-1', 'Alcaldía Municipal de Montería', true),
('892200839-7', 'Alcaldía Municipal de Santiago de Tolú', true),
('890900286-6', 'Gobernación de Antioquia', true),
('800103935-6', 'Gobernación de Córdoba', true),
('892399999-1', 'Gobernación del Cesar', true),
('901034433',   'Establecimiento Público Ambiental Barranquilla Verde', true),
('GEN-001',     'Genesys I+D APEX 24.2', true),
('GEN-002',     'Genesys I+D APEX 19.1', true),
('GEN-003',     'Genesys (Plataforma Principal)', true)
ON CONFLICT (nit) DO NOTHING;

COMMENT ON TABLE entidades_fiscalizadoras IS
  'Entidades fiscalizadoras (municipios, departamentos, EPA) que solicitan análisis del ICA. NO son los contribuyentes analizados.';
