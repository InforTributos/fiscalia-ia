CREATE TABLE hallazgos_fiscales (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nit VARCHAR(20) NOT NULL,
    regla VARCHAR(20) NOT NULL,
    periodo VARCHAR(20) NOT NULL,
    tipo_hallazgo VARCHAR(40) NOT NULL,
    fuerza_probatoria VARCHAR(20) NOT NULL,
    brecha_valor DECIMAL(18,2) DEFAULT 0,
    impuesto_estimado DECIMAL(18,2) DEFAULT 0,
    score DECIMAL(5,2) NOT NULL,
    score_componentes JSONB NOT NULL DEFAULT '{}'::jsonb,
    ventana_limite DATE NOT NULL,
    accionable BOOLEAN NOT NULL DEFAULT TRUE,
    estado VARCHAR(30) NOT NULL DEFAULT 'DETECTADO',
    resumen TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE hallazgo_evidencias (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hallazgo_id UUID NOT NULL REFERENCES hallazgos_fiscales(id) ON DELETE CASCADE,
    fuente VARCHAR(80) NOT NULL,
    referencia_registro VARCHAR(200),
    descripcion TEXT NOT NULL,
    snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE hallazgo_revisiones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hallazgo_id UUID NOT NULL REFERENCES hallazgos_fiscales(id) ON DELETE CASCADE,
    funcionario_id VARCHAR(80) NOT NULL,
    decision VARCHAR(30) NOT NULL,
    motivo TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_hallazgos_nit_periodo ON hallazgos_fiscales(nit, periodo);
CREATE INDEX idx_hallazgos_estado_score ON hallazgos_fiscales(estado, score DESC);
CREATE INDEX idx_hallazgos_regla ON hallazgos_fiscales(regla);
CREATE INDEX idx_hallazgos_accionable ON hallazgos_fiscales(accionable);
CREATE INDEX idx_hallazgo_evidencias_hallazgo ON hallazgo_evidencias(hallazgo_id);

