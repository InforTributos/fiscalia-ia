CREATE TABLE hallazgo_revisiones_agente (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hallazgo_id UUID NOT NULL REFERENCES hallazgos_fiscales(id) ON DELETE CASCADE,
    agente VARCHAR(80) NOT NULL,
    version VARCHAR(30) NOT NULL,
    resultado JSONB NOT NULL DEFAULT '{}'::jsonb,
    modo_degradado BOOLEAN NOT NULL DEFAULT FALSE,
    tokens_entrada INTEGER DEFAULT 0,
    tokens_salida INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_revision_agente_hallazgo ON hallazgo_revisiones_agente(hallazgo_id);
CREATE INDEX idx_revision_agente_created ON hallazgo_revisiones_agente(created_at DESC);

