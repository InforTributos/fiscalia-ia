-- FiscalIA - DDL Tablas Principales
-- Oracle Database 19c+
-- Schema: Taxation Smart Valledupar

CREATE TABLE FISCAL_CAMPANAS (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre VARCHAR2(200) NOT NULL,
    periodo_ini DATE NOT NULL,
    periodo_fin DATE NOT NULL,
    sector_ciiu VARCHAR2(10),
    estado VARCHAR2(20) DEFAULT 'ACTIVA',
    config_json CLOB,
    fecha_crea DATE DEFAULT SYSDATE,
    usuario_id NUMBER
);

CREATE TABLE FISCAL_EXPEDIENTES (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    campana_id NUMBER NOT NULL REFERENCES FISCAL_CAMPANAS(id),
    nit VARCHAR2(20) NOT NULL,
    razon_social VARCHAR2(300),
    numero_exp VARCHAR2(30) UNIQUE NOT NULL,
    estado VARCHAR2(30) DEFAULT 'ABIERTO',
    funcionario_id NUMBER,
    fecha_apertura DATE DEFAULT SYSDATE
);

CREATE TABLE FISCAL_CRUCES (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    expediente_id NUMBER NOT NULL REFERENCES FISCAL_EXPEDIENTES(id),
    fuente VARCHAR2(30) NOT NULL,
    fecha_consulta TIMESTAMP DEFAULT SYSTIMESTAMP,
    resultado_json CLOB,
    score_aporte NUMBER(5,2),
    usuario_audit VARCHAR2(50)
);

CREATE TABLE FISCAL_SCORE_RIESGO (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    expediente_id NUMBER NOT NULL REFERENCES FISCAL_EXPEDIENTES(id),
    srf_total NUMBER(5,2),
    comp_exogena NUMBER(5,2),
    comp_tarifa NUMBER(5,2),
    comp_omision NUMBER(5,2),
    comp_rues NUMBER(5,2),
    explicacion_clob CLOB,
    fecha_calculo DATE DEFAULT SYSDATE
);

CREATE TABLE FISCAL_OMISOS (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    campana_id NUMBER NOT NULL REFERENCES FISCAL_CAMPANAS(id),
    fuente_deteccion VARCHAR2(30),
    nit VARCHAR2(20) NOT NULL,
    razon_social VARCHAR2(300),
    actividad_ciiu VARCHAR2(10),
    evidencia_json CLOB,
    estado VARCHAR2(20) DEFAULT 'PENDIENTE',
    funcionario_id NUMBER,
    brecha_estimada NUMBER(18,2)
);

CREATE TABLE FISCAL_INCONSISTENCIAS (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    expediente_id NUMBER NOT NULL REFERENCES FISCAL_EXPEDIENTES(id),
    declaracion_id NUMBER,
    tipo_inc VARCHAR2(50) NOT NULL,
    descripcion CLOB,
    valor_declarado NUMBER(18,2),
    valor_referencia NUMBER(18,2),
    diferencia NUMBER(18,2),
    fuente_ref VARCHAR2(100),
    estado_hitl VARCHAR2(20) DEFAULT 'PENDIENTE',
    analisis_ia CLOB
);

CREATE TABLE FISCAL_ANALISIS_IA (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    expediente_id NUMBER REFERENCES FISCAL_EXPEDIENTES(id),
    tipo_analisis VARCHAR2(30) NOT NULL,
    prompt_enviado CLOB,
    respuesta_ia CLOB,
    tokens_entrada NUMBER,
    tokens_salida NUMBER,
    costo_estimado NUMBER(10,4),
    fecha_analisis TIMESTAMP DEFAULT SYSTIMESTAMP,
    cache_hit NUMBER(1) DEFAULT 0
);

CREATE TABLE FISCAL_HITL_LOG (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    expediente_id NUMBER NOT NULL REFERENCES FISCAL_EXPEDIENTES(id),
    agente_origen VARCHAR2(20),
    decision_ia VARCHAR2(100),
    accion_humano VARCHAR2(100),
    usuario_id NUMBER,
    timestamp_op TIMESTAMP DEFAULT SYSTIMESTAMP,
    justificacion VARCHAR2(500)
);

CREATE TABLE FISCAL_AUDIT_LOG (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario VARCHAR2(50),
    fecha_ope TIMESTAMP DEFAULT SYSTIMESTAMP,
    tipo_accion VARCHAR2(50),
    nit_afectado VARCHAR2(20),
    ip_origen VARCHAR2(50),
    tabla_afectada VARCHAR2(50),
    descripcion VARCHAR2(500)
);

CREATE TABLE FISCAL_PESOS (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    parametro VARCHAR2(100) UNIQUE NOT NULL,
    valor NUMBER(10,4) NOT NULL,
    descripcion VARCHAR2(300),
    fecha_modif DATE DEFAULT SYSDATE,
    usuario_modif VARCHAR2(50)
);

-- Parámetros iniciales
INSERT INTO FISCAL_PESOS (parametro, valor, descripcion) VALUES ('PCT_SUBDECLARACION', 15, 'Umbral mínimo de diferencia exógena vs ICA para alerta (%)');
INSERT INTO FISCAL_PESOS (parametro, valor, descripcion) VALUES ('PCT_VARIACION_HISTORICA', 30, 'Umbral de variación histórica para alerta (%)');
INSERT INTO FISCAL_PESOS (parametro, valor, descripcion) VALUES ('PESO_EXOGENA', 35, 'Peso del componente exógena en SRF');
INSERT INTO FISCAL_PESOS (parametro, valor, descripcion) VALUES ('PESO_OMISION', 20, 'Peso del componente omisión en SRF');
INSERT INTO FISCAL_PESOS (parametro, valor, descripcion) VALUES ('PESO_TARIFA', 25, 'Peso del componente tarifa CIIU en SRF');
INSERT INTO FISCAL_PESOS (parametro, valor, descripcion) VALUES ('PESO_RUES', 20, 'Peso del componente estado RUES en SRF');
INSERT INTO FISCAL_PESOS (parametro, valor, descripcion) VALUES ('SRF_ALTO', 70, 'Umbral mínimo para considerar SRF ALTO');
INSERT INTO FISCAL_PESOS (parametro, valor, descripcion) VALUES ('SRF_MEDIO', 40, 'Umbral mínimo para considerar SRF MEDIO');

COMMIT;
