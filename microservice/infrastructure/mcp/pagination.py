import logging

from infrastructure.mcp.oracle_adapter import OracleClient

logger = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE = 100


def _count_wrapper(sql: str) -> str:
    """Envuelve un SELECT paginado en SELECT COUNT(*) sin OFFSET/FETCH."""
    base = sql.replace("OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY", "")
    return f"SELECT COUNT(*) AS cnt FROM ({base}) sub"


def calcular_page_size_dinamico(total: int) -> int:
    """Calcula page_size óptimo para Oracle según total estimado de filas."""
    if total <= 0:
        return DEFAULT_PAGE_SIZE
    if total < DEFAULT_PAGE_SIZE:
        return total
    return DEFAULT_PAGE_SIZE

# ID numérico del impuesto ICA en DF_C_IMPUESTOS
ID_IMPSTO_ICA = 102

# ID_PRGRMA en FI_D_PROGRAMAS para "OMISOS" (CDGO_PRGRMA='O') e "INEXACTOS" (CDGO_PRGRMA='I')
ID_PRGRMA_OMISOS = 2
ID_PRGRMA_INEXACTOS = 22

# ID_FRMLRIO_RGION_ATRBTO de los atributos CÓDIGO CIIU en el FUN (formularios V2020, V2025)
CIIU_IDS = "5125, 4971"
# ID_FRMLRIO_RGION_ATRBTO de TARIFA (por mil) en el FUN (V2020, V2024, V2025)
TARIFA_IDS = "2107, 4371, 4874"
# ID_FRMLRIO_RGION_ATRBTO de RETENCIONES recibidas en el FUN
RET_RECIBIDAS_IDS = "2135, 4416, 4919"
# ID_FRMLRIO_RGION_ATRBTO de AUTORRETENCIONES practicadas en el FUN
RET_PRACTICADAS_IDS = "2136, 4417, 4920"

PAGINAR_CONTRIBUYENTES_SQL = """
SELECT c.nit, c.razon_social, c.ciiu, c.regimen
FROM contribuyentes c
WHERE c.tipo_regimen = :tipo_regimen
  AND c.ciiu IN ({actividades_placeholders})
  AND c.vigencia >= TO_DATE(:vigencia_ini, 'YYYY-MM-DD')
  AND c.vigencia <= TO_DATE(:vigencia_fin, 'YYYY-MM-DD')
ORDER BY c.nit
OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
"""

OBTENER_CONTRIBUYENTE_SQL = """
SELECT s.idntfccion AS nit, p.nmbre_rzon_scial AS razon_social,
       p.id_actvdad_ecnmca AS ciiu, se.cdgo_sjto_estdo AS regimen,
       si.id_sjto_impsto
FROM GENESYS.SI_C_SUJETOS s
JOIN GENESYS.SI_I_SUJETOS_IMPUESTO si ON s.id_sjto = si.id_sjto
JOIN GENESYS.SI_I_PERSONAS p ON si.id_sjto_impsto = p.id_sjto_impsto
LEFT JOIN GENESYS.DF_S_SUJETOS_ESTADO se ON si.id_sjto_estdo = se.id_sjto_estdo
JOIN GENESYS.DF_C_IMPUESTOS i ON si.id_impsto = i.id_impsto
WHERE s.idntfccion = :nit AND i.cdgo_impsto = 'ICA'
"""

OBTENER_DECLARACIONES_SQL = """
SELECT d.vgncia AS periodo, d.bse_grvble AS base_gravable,
       d.vlor_ttal AS impuesto, d.vlor_pago
FROM GENESYS.GI_G_DECLARACIONES d
JOIN GENESYS.GI_D_DCLRCNES_VGNCIAS_FRMLR dvf
    ON d.id_dclrcion_vgncia_frmlrio = dvf.id_dclrcion_vgncia_frmlrio
JOIN GENESYS.GI_D_FORMULARIOS f ON dvf.id_frmlrio = f.id_frmlrio
WHERE d.id_sjto_impsto = :id_sjto_impsto
  AND d.vgncia = :periodo
  AND d.cdgo_dclrcion_estdo = 'PRS'
  AND d.fcha_anlcion IS NULL
  AND f.cdgo_frmlrio LIKE 'FUN%'
ORDER BY d.vgncia
"""

OBTENER_EXOGENA_SQL = """
SELECT vgncia_rtncion AS periodo, SUM(vlor_rtncion) AS ingresos
FROM GENESYS.GI_G_EXOGENA_RETENCIONES
WHERE idntfccion = :nit AND vgncia_rtncion = :periodo
GROUP BY vgncia_rtncion
ORDER BY vgncia_rtncion
"""


async def paginar_contribuyentes(
    client: OracleClient,
    vigencia_ini: str,
    vigencia_fin: str,
    tipo_regimen: str,
    actividades_economicas: list[str],
    periodo: str,
    page_size: int = DEFAULT_PAGE_SIZE,
):
    actividades_placeholders = ", ".join(f":a{i}" for i in range(len(actividades_economicas)))
    sql = PAGINAR_CONTRIBUYENTES_SQL.format(actividades_placeholders=actividades_placeholders)

    bind_params = {
        "tipo_regimen": tipo_regimen,
        "vigencia_ini": vigencia_ini,
        "vigencia_fin": vigencia_fin,
        **{f"a{i}": act for i, act in enumerate(actividades_economicas)},
    }

    offset = 0
    total_obtenidos = 0

    while True:
        logger.info("Oracle: solicitando offset=%d limit=%d", offset, page_size)
        params = {**bind_params, "offset": offset, "limit": page_size}
        result = await client.execute_sql(sql, params)

        if not result:
            break

        items = result if isinstance(result, list) else [result]
        if not items:
            break

        for item in items:
            yield item
            total_obtenidos += 1

        if len(items) < page_size:
            break

        offset += page_size

    logger.info("Paginacion completada — %d contribuyentes obtenidos", total_obtenidos)


async def obtener_datos_fiscales(client: OracleClient, contribuyente_nit: str, periodo: str) -> dict | None:
    logger.info("Oracle: solicitando datos fiscales para NIT %s periodo %s", contribuyente_nit, periodo)

    contribuyente = await client.execute_sql(OBTENER_CONTRIBUYENTE_SQL, {"nit": contribuyente_nit})

    if not contribuyente:
        return None

    row = contribuyente[0] if isinstance(contribuyente, list) else contribuyente
    id_sjto_impsto = row.get("id_sjto_impsto")

    declaraciones = []
    exogena = []
    if id_sjto_impsto:
        declaraciones = await client.execute_sql(
            OBTENER_DECLARACIONES_SQL,
            {"id_sjto_impsto": id_sjto_impsto, "periodo": periodo},
        )
        exogena = await client.execute_sql(OBTENER_EXOGENA_SQL, {"nit": contribuyente_nit, "periodo": periodo})

    return {
        "contribuyente_nit": row.get("nit", contribuyente_nit),
        "razon_social": row.get("razon_social", ""),
        "ciiu": str(row.get("ciiu", "") or ""),
        "regimen": row.get("regimen", ""),
        "declaraciones_ica": declaraciones if isinstance(declaraciones, list) else [],
        "exogena_dian": exogena if isinstance(exogena, list) else [],
        "rues_estado": "",
    }


OMISOS_CONOCIDOS_SQL = """
SELECT s.idntfccion, p.nmbre_rzon_scial, p.id_actvdad_ecnmca,
       si.id_sjto_impsto, si.id_sjto_estdo, p.fcha_incio_actvddes, s.drccion
FROM SI_I_SUJETOS_IMPUESTO si
JOIN SI_I_PERSONAS p ON si.id_sjto_impsto = p.id_sjto_impsto
JOIN SI_C_SUJETOS s ON si.id_sjto = s.id_sjto
WHERE si.id_impsto = :id_impsto_ica
  AND si.estdo_blqdo = 'N'
  AND p.fcha_incio_actvddes <= TO_DATE(:fin_periodo, 'YYYY-MM-DD')
  AND (si.fcha_cnclcion IS NULL OR si.fcha_cnclcion > TO_DATE(:fin_periodo, 'YYYY-MM-DD'))
  AND NOT EXISTS (
    SELECT 1 FROM GI_G_DECLARACIONES d
    JOIN GI_D_DCLRCNES_VGNCIAS_FRMLR dvf
        ON d.id_dclrcion_vgncia_frmlrio = dvf.id_dclrcion_vgncia_frmlrio
    JOIN GI_D_FORMULARIOS f ON dvf.id_frmlrio = f.id_frmlrio
    WHERE d.id_sjto_impsto = si.id_sjto_impsto
      AND d.vgncia = :vigencia
      AND d.cdgo_dclrcion_estdo = 'PRS'
      AND d.fcha_anlcion IS NULL
      AND f.cdgo_frmlrio LIKE 'FUN%'
      {payment_filter}
  )
  AND NOT EXISTS (
    SELECT 1 FROM FI_G_CANDIDATOS c
    JOIN FI_G_CANDIDATOS_VIGENCIA cv ON c.id_cnddto = cv.id_cnddto
    JOIN FI_G_FSCLZC_EXPDN_CNDD_VGNC ev ON cv.id_cnddto_vgncia = ev.id_cnddto_vgncia
    WHERE c.id_sjto_impsto = si.id_sjto_impsto
      AND c.id_prgrma = :id_prgrma_omisos
      AND cv.vgncia = :vigencia
  )
ORDER BY s.idntfccion
OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
"""

OMISOS_DESCONOCIDOS_DIAN_SQL = """
SELECT d.nit, d.razon_social, d.ciiu, d.valor_dian, d.vigencia, 'DIAN' AS fuente
FROM TEMP_RQ_DIAN d
WHERE d.vigencia = :vigencia
  AND NOT EXISTS (
    SELECT 1 FROM SI_C_SUJETOS s WHERE s.idntfccion = d.nit
  )
  AND NOT EXISTS (
    SELECT 1 FROM FI_G_CANDIDATOS c
    JOIN FI_G_CANDIDATOS_VIGENCIA cv ON c.id_cnddto = cv.id_cnddto
    WHERE c.id_sjto_impsto IN (
      SELECT si2.id_sjto_impsto FROM SI_I_SUJETOS_IMPUESTO si2
      JOIN SI_C_SUJETOS s2 ON si2.id_sjto = s2.id_sjto
      WHERE s2.idntfccion = d.nit
    )
    AND c.id_prgrma = :id_prgrma_omisos
    AND cv.vgncia = :vigencia
  )
OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
"""

INEXACTOS_CIIU_SQL = """
SELECT s.idntfccion, p.nmbre_rzon_scial,
       TO_CHAR(det_ciiu.vlor) AS ciiu_declarado,
       TO_CHAR(det_tarifa.vlor) AS tarifa_declarada,
       dian.ciiu AS ciiu_dian,
       dian.tarifa AS tarifa_dian
FROM GI_G_DECLARACIONES decl
JOIN GI_D_DCLRCNES_VGNCIAS_FRMLR dvf
    ON decl.id_dclrcion_vgncia_frmlrio = dvf.id_dclrcion_vgncia_frmlrio
JOIN GI_D_FORMULARIOS frm ON dvf.id_frmlrio = frm.id_frmlrio
JOIN SI_I_SUJETOS_IMPUESTO si ON decl.id_sjto_impsto = si.id_sjto_impsto
JOIN SI_I_PERSONAS p ON si.id_sjto_impsto = p.id_sjto_impsto
JOIN SI_C_SUJETOS s ON si.id_sjto = s.id_sjto
JOIN GI_G_DECLARACIONES_DETALLE det_ciiu
  ON decl.id_dclrcion = det_ciiu.id_dclrcion
  AND det_ciiu.id_frmlrio_rgion_atrbto IN ({ciiu_ids})
JOIN GI_G_DECLARACIONES_DETALLE det_tarifa
  ON decl.id_dclrcion = det_tarifa.id_dclrcion
  AND det_tarifa.id_frmlrio_rgion_atrbto IN ({tarifa_ids})
JOIN TEMP_RQ_DIAN dian ON s.idntfccion = dian.nit AND dian.vigencia = :vigencia
WHERE decl.vgncia = :vigencia
  AND decl.cdgo_dclrcion_estdo = 'PRS'
  AND decl.fcha_anlcion IS NULL
  AND frm.cdgo_frmlrio LIKE 'FUN%'
  {payment_filter}
  AND CAST(det_ciiu.vlor AS VARCHAR2(10)) != dian.ciiu
  AND TO_NUMBER(CAST(det_tarifa.vlor AS VARCHAR2(10)), '9999999D99', 'NLS_NUMERIC_CHARACTERS=''.,''') < dian.tarifa
  AND NOT EXISTS (
    SELECT 1 FROM FI_G_CANDIDATOS c
    JOIN FI_G_CANDIDATOS_VIGENCIA cv ON c.id_cnddto = cv.id_cnddto
    WHERE c.id_sjto_impsto = si.id_sjto_impsto
      AND c.id_prgrma = :id_prgrma_inexactos
      AND cv.vgncia = :vigencia
  )
OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
"""

INEXACTOS_RETENCIONES_SQL = """
SELECT s.idntfccion, p.nmbre_rzon_scial,
       TO_CHAR(det_ret_recibidas.vlor) AS retenciones_declaradas_recibidas,
       TO_CHAR(det_ret_practicadas.vlor) AS retenciones_declaradas_practicadas,
       exo_recibidas.total_exo AS retenciones_exogena_recibidas,
       exo_practicadas.total_exo AS retenciones_exogena_practicadas
FROM GI_G_DECLARACIONES decl
JOIN GI_D_DCLRCNES_VGNCIAS_FRMLR dvf
    ON decl.id_dclrcion_vgncia_frmlrio = dvf.id_dclrcion_vgncia_frmlrio
JOIN GI_D_FORMULARIOS frm ON dvf.id_frmlrio = frm.id_frmlrio
JOIN SI_I_SUJETOS_IMPUESTO si ON decl.id_sjto_impsto = si.id_sjto_impsto
JOIN SI_I_PERSONAS p ON si.id_sjto_impsto = p.id_sjto_impsto
JOIN SI_C_SUJETOS s ON si.id_sjto = s.id_sjto
LEFT JOIN GI_G_DECLARACIONES_DETALLE det_ret_recibidas
  ON decl.id_dclrcion = det_ret_recibidas.id_dclrcion
  AND det_ret_recibidas.id_frmlrio_rgion_atrbto IN ({ret_recibidas_ids})
LEFT JOIN GI_G_DECLARACIONES_DETALLE det_ret_practicadas
  ON decl.id_dclrcion = det_ret_practicadas.id_dclrcion
  AND det_ret_practicadas.id_frmlrio_rgion_atrbto IN ({ret_practicadas_ids})
LEFT JOIN (
  SELECT idntfccion, SUM(vlor_rtncion) AS total_exo
  FROM GI_G_EXOGENA_RETENCIONES
  WHERE vgncia_rtncion = :vigencia
    AND cdgo_exgna_tpo_rgstro = 'RECIBIDA'
  GROUP BY idntfccion
) exo_recibidas ON s.idntfccion = exo_recibidas.idntfccion
LEFT JOIN (
  SELECT idntfccion, SUM(vlor_rtncion) AS total_exo
  FROM GI_G_EXOGENA_RETENCIONES
  WHERE vgncia_rtncion = :vigencia
    AND cdgo_exgna_tpo_rgstro = 'PRACTICADA'
  GROUP BY idntfccion
) exo_practicadas ON s.idntfccion = exo_practicadas.idntfccion
WHERE decl.vgncia = :vigencia
  AND decl.cdgo_dclrcion_estdo = 'PRS'
  AND decl.fcha_anlcion IS NULL
  AND frm.cdgo_frmlrio LIKE 'FUN%'
  {payment_filter}
  AND (
    ABS(NVL(TO_NUMBER(CAST(det_ret_recibidas.vlor AS VARCHAR2(50)), '99999999999999999999D99', 'NLS_NUMERIC_CHARACTERS=''.,'''), 0) - NVL(exo_recibidas.total_exo, 0))
      > :umbral * GREATEST(NVL(TO_NUMBER(CAST(det_ret_recibidas.vlor AS VARCHAR2(50)), '99999999999999999999D99', 'NLS_NUMERIC_CHARACTERS=''.,'''), 0), NVL(exo_recibidas.total_exo, 0), 1)
    OR
    ABS(NVL(TO_NUMBER(CAST(det_ret_practicadas.vlor AS VARCHAR2(50)), '99999999999999999999D99', 'NLS_NUMERIC_CHARACTERS=''.,'''), 0) - NVL(exo_practicadas.total_exo, 0))
      > :umbral * GREATEST(NVL(TO_NUMBER(CAST(det_ret_practicadas.vlor AS VARCHAR2(50)), '99999999999999999999D99', 'NLS_NUMERIC_CHARACTERS=''.,'''), 0), NVL(exo_practicadas.total_exo, 0), 1)
  )
OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
"""


async def obtener_omisos_conocidos(client: OracleClient, vigencia, periodo, page_size=None):
    sql = OMISOS_CONOCIDOS_SQL.format(payment_filter="")
    size = page_size or DEFAULT_PAGE_SIZE
    offset_val = 0
    total = 0

    while True:
        params = {
            "id_impsto_ica": ID_IMPSTO_ICA,
            "id_prgrma_omisos": ID_PRGRMA_OMISOS,
            "vigencia": vigencia,
            "fin_periodo": f"{vigencia}-12-31",
            "offset": offset_val,
            "limit": size,
        }
        result = await client.execute_sql(sql, params)
        if not result:
            break
        items = result if isinstance(result, list) else [result]
        if not items:
            break
        for item in items:
            yield item
            total += 1
        if len(items) < size:
            break
        offset_val += size

    logger.info("Omisos conocidos: %d candidatos obtenidos", total)


async def obtener_omisos_desconocidos(client: OracleClient, vigencia, page_size=None):
    size = page_size or DEFAULT_PAGE_SIZE
    offset_val = 0
    total = 0

    while True:
        params = {
            "id_prgrma_omisos": ID_PRGRMA_OMISOS,
            "vigencia": vigencia,
            "offset": offset_val,
            "limit": size,
        }
        result = await client.execute_sql(OMISOS_DESCONOCIDOS_DIAN_SQL, params)
        if not result:
            break
        items = result if isinstance(result, list) else [result]
        if not items:
            break
        for item in items:
            yield item
            total += 1
        if len(items) < size:
            break
        offset_val += size

    logger.info("Omisos desconocidos: %d candidatos obtenidos", total)


async def obtener_inexactos_ciiu(client: OracleClient, periodo, page_size=None):
    sql = INEXACTOS_CIIU_SQL.format(ciiu_ids=CIIU_IDS, tarifa_ids=TARIFA_IDS, payment_filter="")
    size = page_size or DEFAULT_PAGE_SIZE
    offset_val = 0
    total = 0
    vigencia = periodo

    while True:
        params = {
            "id_prgrma_inexactos": ID_PRGRMA_INEXACTOS,
            "vigencia": vigencia,
            "offset": offset_val,
            "limit": size,
        }
        result = await client.execute_sql(sql, params)
        if not result:
            break
        items = result if isinstance(result, list) else [result]
        if not items:
            break
        for item in items:
            yield item
            total += 1
        if len(items) < size:
            break
        offset_val += size

    logger.info("Inexactos CIIU: %d candidatos obtenidos", total)


async def obtener_inexactos_retenciones(
    client: OracleClient, periodo, page_size=None, umbral_pct=None,
):
    sql = INEXACTOS_RETENCIONES_SQL.format(
        ret_recibidas_ids=RET_RECIBIDAS_IDS,
        ret_practicadas_ids=RET_PRACTICADAS_IDS,
        payment_filter="",
    )
    size = page_size or DEFAULT_PAGE_SIZE
    offset_val = 0
    total = 0
    vigencia = periodo
    umbral = (umbral_pct or 5.0) / 100.0

    while True:
        params = {
            "vigencia": vigencia,
            "umbral": umbral,
            "offset": offset_val,
            "limit": size,
        }
        result = await client.execute_sql(sql, params)
        if not result:
            break
        items = result if isinstance(result, list) else [result]
        if not items:
            break
        for item in items:
            yield item
            total += 1
        if len(items) < size:
            break
        offset_val += size

    logger.info("Inexactos retenciones: %d candidatos obtenidos", total)


async def contar_omisos_conocidos(client: OracleClient, vigencia, periodo) -> int:
    sql = _count_wrapper(OMISOS_CONOCIDOS_SQL.format(payment_filter=""))
    params = {
        "id_impsto_ica": ID_IMPSTO_ICA,
        "id_prgrma_omisos": ID_PRGRMA_OMISOS,
        "vigencia": vigencia,
        "fin_periodo": f"{vigencia}-12-31",
    }
    result = await client.execute_sql(sql, params)
    if not result:
        return 0
    row = result[0] if isinstance(result, list) else result
    return row.get("cnt", 0) or 0


async def contar_omisos_desconocidos(client: OracleClient, vigencia) -> int:
    sql = _count_wrapper(OMISOS_DESCONOCIDOS_DIAN_SQL)
    params = {
        "id_prgrma_omisos": ID_PRGRMA_OMISOS,
        "vigencia": vigencia,
    }
    result = await client.execute_sql(sql, params)
    if not result:
        return 0
    row = result[0] if isinstance(result, list) else result
    return row.get("cnt", 0) or 0


async def contar_inexactos_ciiu(client: OracleClient, periodo) -> int:
    sql = _count_wrapper(INEXACTOS_CIIU_SQL.format(
        ciiu_ids=CIIU_IDS, tarifa_ids=TARIFA_IDS, payment_filter="",
    ))
    params = {
        "id_prgrma_inexactos": ID_PRGRMA_INEXACTOS,
        "vigencia": periodo,
    }
    result = await client.execute_sql(sql, params)
    if not result:
        return 0
    row = result[0] if isinstance(result, list) else result
    return row.get("cnt", 0) or 0


async def contar_inexactos_retenciones(client: OracleClient, periodo, umbral_pct=None) -> int:
    sql = _count_wrapper(INEXACTOS_RETENCIONES_SQL.format(
        ret_recibidas_ids=RET_RECIBIDAS_IDS,
        ret_practicadas_ids=RET_PRACTICADAS_IDS,
        payment_filter="",
    ))
    umbral = (umbral_pct or 5.0) / 100.0
    params = {
        "vigencia": periodo,
        "umbral": umbral,
    }
    result = await client.execute_sql(sql, params)
    if not result:
        return 0
    row = result[0] if isinstance(result, list) else result
    return row.get("cnt", 0) or 0
