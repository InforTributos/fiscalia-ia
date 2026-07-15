CREATE TABLE clientes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nit VARCHAR(20) UNIQUE NOT NULL,
    razon_social VARCHAR(500) NOT NULL,
    email VARCHAR(200),
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE procesos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cliente_id UUID REFERENCES clientes(id),
    nombre VARCHAR(200) NOT NULL,
    estado VARCHAR(30) NOT NULL DEFAULT 'PENDIENTE',
    criteria JSONB NOT NULL,
    total_nits INTEGER DEFAULT 0,
    candidatos INTEGER DEFAULT 0,
    omisos INTEGER DEFAULT 0,
    exactos INTEGER DEFAULT 0,
    inexactos INTEGER DEFAULT 0,
    intentos_total INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE proceso_intentos (
    id SERIAL PRIMARY KEY,
    proceso_id UUID REFERENCES procesos(id),
    numero_intento INTEGER NOT NULL DEFAULT 1,
    estado VARCHAR(30) NOT NULL DEFAULT 'EN_PROCESO',
    procesados INTEGER DEFAULT 0,
    errores_count INTEGER DEFAULT 0,
    error_resumen TEXT,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE TABLE proceso_detalle (
    id SERIAL PRIMARY KEY,
    proceso_id UUID REFERENCES procesos(id),
    intento_id INTEGER REFERENCES proceso_intentos(id),
    nit VARCHAR(20) NOT NULL,
    razon_social VARCHAR(500),
    ciiu VARCHAR(10),
    mcp_score DECIMAL(10,2),
    es_candidato BOOLEAN DEFAULT TRUE,
    mcp_razon TEXT,
    clasificacion VARCHAR(20) NOT NULL,
    detalle_clasificacion TEXT,
    srf_total DECIMAL(5,2),
    nivel_riesgo VARCHAR(10),
    hallazgos JSONB,
    explicacion_ia TEXT,
    tokens_entrada INTEGER,
    tokens_salida INTEGER,
    costo_estimado DECIMAL(10,4),
    pagina INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE proceso_errores (
    id SERIAL PRIMARY KEY,
    proceso_id UUID REFERENCES procesos(id),
    intento_id INTEGER REFERENCES proceso_intentos(id),
    capa VARCHAR(30) NOT NULL,
    codigo VARCHAR(50) NOT NULL,
    mensaje TEXT NOT NULL,
    contexto JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE proceso_detalle_errores (
    id SERIAL PRIMARY KEY,
    detalle_id INTEGER REFERENCES proceso_detalle(id),
    proceso_id UUID NOT NULL REFERENCES procesos(id),
    nit VARCHAR(20) NOT NULL,
    capa VARCHAR(30) NOT NULL,
    codigo VARCHAR(50) NOT NULL,
    mensaje TEXT NOT NULL,
    contexto JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_procesos_estado ON procesos(estado);
CREATE INDEX idx_procesos_cliente ON procesos(cliente_id);
CREATE INDEX idx_proceso_intentos_proceso ON proceso_intentos(proceso_id);
CREATE INDEX idx_proceso_intentos_estado ON proceso_intentos(estado);
CREATE INDEX idx_proceso_detalle_proceso ON proceso_detalle(proceso_id);
CREATE INDEX idx_proceso_detalle_intento ON proceso_detalle(intento_id);
CREATE INDEX idx_proceso_detalle_nit ON proceso_detalle(nit);
CREATE INDEX idx_proceso_detalle_clasificacion ON proceso_detalle(clasificacion);
CREATE INDEX idx_proceso_errores_proceso ON proceso_errores(proceso_id);
CREATE INDEX idx_proceso_errores_intento ON proceso_errores(intento_id);
CREATE INDEX idx_proceso_errores_capa ON proceso_errores(capa);
CREATE INDEX idx_detalle_errores_detalle ON proceso_detalle_errores(detalle_id);
CREATE INDEX idx_detalle_errores_proceso ON proceso_detalle_errores(proceso_id);
