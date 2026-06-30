import logging

from infrastructure.mcp.oracle_adapter import MCPClient

logger = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE = 100

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
SELECT c.nit, c.razon_social, c.ciiu, c.regimen, r.rues_estado
FROM contribuyentes c
LEFT JOIN rues r ON c.nit = r.nit
WHERE c.nit = :nit
"""

OBTENER_DECLARACIONES_SQL = """
SELECT periodo, base_gravable, tarifa, impuesto
FROM declaraciones_ica
WHERE nit = :nit AND periodo = :periodo
ORDER BY periodo
"""

OBTENER_EXOGENA_SQL = """
SELECT periodo, ingresos
FROM exogena_dian
WHERE nit = :nit AND periodo = :periodo
ORDER BY periodo
"""


async def paginar_contribuyentes(
    client: MCPClient,
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
        logger.info("MCP: solicitando offset=%d limit=%d", offset, page_size)
        params = {**bind_params, "offset": offset, "limit": page_size}
        result = await client.call_tool("EXECUTE_SQL", {
            "query": sql,
            "bind_params": params,
        })

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

    logger.info("MCP: paginación completada — %d contribuyentes obtenidos", total_obtenidos)


async def obtener_datos_fiscales(client: MCPClient, nit: str, periodo: str) -> dict | None:
    logger.info("MCP: solicitando datos fiscales para NIT %s periodo %s", nit, periodo)

    contribuyente = await client.call_tool("EXECUTE_SQL", {
        "query": OBTENER_CONTRIBUYENTE_SQL,
        "bind_params": {"nit": nit},
    })

    if not contribuyente:
        return None

    row = contribuyente[0] if isinstance(contribuyente, list) else contribuyente

    declaraciones = await client.call_tool("EXECUTE_SQL", {
        "query": OBTENER_DECLARACIONES_SQL,
        "bind_params": {"nit": nit, "periodo": periodo},
    })
    exogena = await client.call_tool("EXECUTE_SQL", {
        "query": OBTENER_EXOGENA_SQL,
        "bind_params": {"nit": nit, "periodo": periodo},
    })

    return {
        "nit": row.get("nit", nit),
        "razon_social": row.get("razon_social", ""),
        "ciiu": row.get("ciiu", ""),
        "regimen": row.get("regimen", ""),
        "declaraciones_ica": declaraciones if isinstance(declaraciones, list) else [],
        "exogena_dian": exogena if isinstance(exogena, list) else [],
        "rues_estado": row.get("rues_estado", ""),
    }


OMISOS_CONOCIDOS_SQL = """
SELECT s.idntfccion, p.nmbre_rzon_scial, p.id_actvdad_ecnmca,
       si.id_sjto_impsto, si.id_sjto_estdo, p.fcha_incio_actvddes, s.drccion
FROM SI_I_SUJETOS_IMPUESTO si
JOIN SI_I_PERSONAS p ON si.id_sjto_impsto = p.id_sjto_impsto
JOIN SI_C_SUJETOS s ON p.id_sjto_impsto = s.id_sjto_impsto
WHERE si.id_impsto = :id_impsto_ica
  AND si.estdo_blqdo = 'N'
  AND p.fcha_incio_actvddes <= TO_DATE(:fin_periodo, 'YYYY-MM-DD')
  AND (si.fcha_cnclcion IS NULL OR si.fcha_cnclcion > TO_DATE(:fin_periodo, 'YYYY-MM-DD'))
  AND NOT EXISTS (
    SELECT 1 FROM GI_G_DECLARACIONES d
    WHERE d.id_sjto_impsto = si.id_sjto_impsto
      AND d.vgncia = :vigencia
      AND d.cdgo_dclrcion_estdo IN ('VIGENTE', 'PRESENTADA')
      AND d.fcha_anlcion IS NULL
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
SELECT d.nit, d.razon_social, d.ciiu, d.valor_dian, d.vgncia, 'DIAN' AS fuente
FROM TEMP_RQ_DIAN d
WHERE d.vgncia = :vigencia
  AND NOT EXISTS (
    SELECT 1 FROM SI_C_SUJETOS s WHERE s.idntfccion = d.nit
  )
  AND NOT EXISTS (
    SELECT 1 FROM FI_G_CANDIDATOS c
    JOIN FI_G_CANDIDATOS_VIGENCIA cv ON c.id_cnddto = cv.id_cnddto
    WHERE c.id_sjto_impsto IN (
      SELECT si2.id_sjto_impsto FROM SI_I_SUJETOS_IMPUESTO si2
      JOIN SI_C_SUJETOS s2 ON si2.id_sjto_impsto = s2.id_sjto_impsto
      WHERE s2.idntfccion = d.nit
    )
    AND c.id_prgrma = :id_prgrma_omisos
    AND cv.vgncia = :vigencia
  )
OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
"""

INEXACTOS_CIIU_SQL = """
SELECT s.idntfccion, p.nmbre_rzon_scial,
       det_ciiu.vlor AS ciiu_declarado,
       det_tarifa.vlor AS tarifa_declarada,
       dian.ciiu AS ciiu_dian,
       dian.trfa AS tarifa_dian
FROM GI_G_DECLARACIONES decl
JOIN SI_I_SUJETOS_IMPUESTO si ON decl.id_sjto_impsto = si.id_sjto_impsto
JOIN SI_I_PERSONAS p ON si.id_sjto_impsto = p.id_sjto_impsto
JOIN SI_C_SUJETOS s ON p.id_sjto_impsto = s.id_sjto_impsto
JOIN GI_G_DECLARACIONES_DETALLE det_ciiu
  ON decl.id_dclrcion = det_ciiu.id_dclrcion
  AND det_ciiu.id_frmlrio_rgion_atrbto IN (5086, 4725)
JOIN GI_G_DECLARACIONES_DETALLE det_tarifa
  ON decl.id_dclrcion = det_tarifa.id_dclrcion
  AND det_tarifa.id_frmlrio_rgion_atrbto IN (5004)
JOIN TEMP_RQ_DIAN dian ON s.idntfccion = dian.nit AND dian.vgncia = :vigencia
WHERE decl.vgncia = :vigencia
  AND decl.cdgo_dclrcion_estdo IN ('VIGENTE', 'PRESENTADA')
  AND decl.fcha_anlcion IS NULL
  AND det_ciiu.vlor != dian.ciiu
  AND TO_NUMBER(det_tarifa.vlor) < TO_NUMBER(dian.trfa)
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
       det_ret_recibidas.vlor AS retenciones_declaradas_recibidas,
       det_ret_practicadas.vlor AS retenciones_declaradas_practicadas,
       exo_recibidas.total_exo AS retenciones_exogena_recibidas,
       exo_practicadas.total_exo AS retenciones_exogena_practicadas
FROM GI_G_DECLARACIONES decl
JOIN SI_I_SUJETOS_IMPUESTO si ON decl.id_sjto_impsto = si.id_sjto_impsto
JOIN SI_I_PERSONAS p ON si.id_sjto_impsto = p.id_sjto_impsto
JOIN SI_C_SUJETOS s ON p.id_sjto_impsto = s.id_sjto_impsto
LEFT JOIN GI_G_DECLARACIONES_DETALLE det_ret_recibidas
  ON decl.id_dclrcion = det_ret_recibidas.id_dclrcion
  AND det_ret_recibidas.id_frmlrio_rgion_atrbto IN (717, 845, 1190, 5035)
LEFT JOIN GI_G_DECLARACIONES_DETALLE det_ret_practicadas
  ON decl.id_dclrcion = det_ret_practicadas.id_dclrcion
  AND det_ret_practicadas.id_frmlrio_rgion_atrbto IN (718, 846, 5036)
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
  AND decl.cdgo_dclrcion_estdo IN ('VIGENTE', 'PRESENTADA')
  AND decl.fcha_anlcion IS NULL
  AND (
    ABS(NVL(TO_NUMBER(det_ret_recibidas.vlor), 0) - NVL(exo_recibidas.total_exo, 0))
      > :umbral * GREATEST(NVL(TO_NUMBER(det_ret_recibidas.vlor), 0), NVL(exo_recibidas.total_exo, 0), 1)
    OR
    ABS(NVL(TO_NUMBER(det_ret_practicadas.vlor), 0) - NVL(exo_practicadas.total_exo, 0))
      > :umbral * GREATEST(NVL(TO_NUMBER(det_ret_practicadas.vlor), 0), NVL(exo_practicadas.total_exo, 0), 1)
  )
OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
"""


async def obtener_omisos_conocidos(client, vigencia, periodo, page_size=None):
    size = page_size or DEFAULT_PAGE_SIZE
    offset_val = 0
    total = 0

    while True:
        params = {
            "id_impsto_ica": "ICA",
            "id_prgrma_omisos": "O",
            "vigencia": vigencia,
            "fin_periodo": f"{vigencia}-12-31",
            "offset": offset_val,
            "limit": size,
        }
        result = await client.call_tool("EXECUTE_SQL", {
            "query": OMISOS_CONOCIDOS_SQL,
            "bind_params": params,
        })
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


async def obtener_omisos_desconocidos(client, vigencia, page_size=None):
    size = page_size or DEFAULT_PAGE_SIZE
    offset_val = 0
    total = 0

    while True:
        params = {
            "id_prgrma_omisos": "O",
            "vigencia": vigencia,
            "offset": offset_val,
            "limit": size,
        }
        result = await client.call_tool("EXECUTE_SQL", {
            "query": OMISOS_DESCONOCIDOS_DIAN_SQL,
            "bind_params": params,
        })
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


async def obtener_inexactos_ciiu(client, periodo, page_size=None):
    size = page_size or DEFAULT_PAGE_SIZE
    offset_val = 0
    total = 0
    vigencia = periodo

    while True:
        params = {
            "id_prgrma_inexactos": "I",
            "vigencia": vigencia,
            "offset": offset_val,
            "limit": size,
        }
        result = await client.call_tool("EXECUTE_SQL", {
            "query": INEXACTOS_CIIU_SQL,
            "bind_params": params,
        })
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


async def obtener_inexactos_retenciones(client, periodo, page_size=None, umbral_pct=None):
    size = page_size or DEFAULT_PAGE_SIZE
    offset_val = 0
    total = 0
    vigencia = periodo
    umbral = (umbral_pct or 5.0) / 100.0

    while True:
        params = {
            "id_prgrma_inexactos": "I",
            "vigencia": vigencia,
            "umbral": umbral,
            "offset": offset_val,
            "limit": size,
        }
        result = await client.call_tool("EXECUTE_SQL", {
            "query": INEXACTOS_RETENCIONES_SQL,
            "bind_params": params,
        })
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
