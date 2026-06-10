-- FiscalIA - Contrato PL/SQL esperado por el microservicio Python
-- Estos packages deben ser implementados por el equipo PL/SQL
-- El microservicio los llama via python-oracledb

-- Package FISCAL_CROSS (AGT-01 CrossCheck)
CREATE OR REPLACE PACKAGE FISCAL_CROSS AS
    FUNCTION obtener_cruces(
        p_nit VARCHAR2,
        p_periodo VARCHAR2
    ) RETURN SYS_REFCURSOR;
    -- Columnas esperadas:
    --   ciiu              VARCHAR2(10)
    --   ingreso_declarado NUMBER(18,2)
    --   ingreso_exogena   NUMBER(18,2)
    --   diferencia        NUMBER(18,2)
    --   variacion_pct     NUMBER(10,2)
    --   umbral_superado   NUMBER(1)
END FISCAL_CROSS;

-- Package FISCAL_INC (AGT-03 InconsistencyAnalyzer)
CREATE OR REPLACE PACKAGE FISCAL_INC AS
    FUNCTION obtener_inconsistencias(
        p_nit VARCHAR2,
        p_periodo VARCHAR2
    ) RETURN SYS_REFCURSOR;
    -- Columnas esperadas:
    --   tipo_incidencia   VARCHAR2(50) -- SUBREGISTRO|TARIFA|PERIODO|EXENCION|BASE_CERO|OTRA
    --   ciiu              VARCHAR2(10)
    --   descripcion       VARCHAR2(500)
    --   valor_declarado   NUMBER(18,2)
    --   valor_referencia  NUMBER(18,2)
    --   diferencia        NUMBER(18,2)
    --   severidad         VARCHAR2(10) -- ALTA|MEDIA|BAJA
END FISCAL_INC;

-- Package FISCAL_SCORE (SRF)
CREATE OR REPLACE PACKAGE FISCAL_SCORE AS
    FUNCTION obtener_srf(
        p_nit VARCHAR2,
        p_periodo VARCHAR2
    ) RETURN SYS_REFCURSOR;
    -- Columnas esperadas:
    --   srf_total         NUMBER(5,2)
    --   comp_exogena      NUMBER(5,2)
    --   comp_tarifa       NUMBER(5,2)
    --   comp_omision      NUMBER(5,2)
    --   comp_rues         NUMBER(5,2)
END FISCAL_SCORE;

-- Package FISCAL_ANALISIS_IA (persistencia)
CREATE OR REPLACE PACKAGE FISCAL_ANALISIS_IA AS
    FUNCTION guardar(
        p_expediente_id   NUMBER,
        p_tipo_analisis   VARCHAR2,
        p_prompt          CLOB,
        p_respuesta_ia    CLOB,
        p_tokens_entrada  NUMBER,
        p_tokens_salida   NUMBER,
        p_costo_estimado  NUMBER,
        p_cache_hit       NUMBER DEFAULT 0
    ) RETURN NUMBER;
END FISCAL_ANALISIS_IA;
