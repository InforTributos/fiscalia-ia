ALTER TABLE proceso_detalle ADD COLUMN mensaje TEXT;
COMMENT ON COLUMN proceso_detalle.mensaje IS 'Razon por la que no se pudo completar el analisis de un NIT (ej: sin datos fiscales, sin historial, CIIU no encontrado en grupo de pares)';
