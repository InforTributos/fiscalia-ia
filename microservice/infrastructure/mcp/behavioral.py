from __future__ import annotations

from infrastructure.mcp.oracle_adapter import OracleClient

CONTRIBUYENTE_LOOKUP_SQL = """
SELECT s.idntfccion AS nit, p.nmbre_rzon_scial AS razon_social,
       p.id_actvdad_ecnmca AS ciiu,
       CASE se.cdgo_sjto_estdo
           WHEN 'A' THEN 'ACTIVO'
           WHEN 'I' THEN 'INACTIVO'
           WHEN 'O' THEN 'OMISO_DESCONOCIDO'
           ELSE ''
       END AS rues_estado,
       si.id_sjto_impsto
FROM GENESYS.SI_C_SUJETOS s
JOIN GENESYS.SI_I_SUJETOS_IMPUESTO si ON s.id_sjto = si.id_sjto
JOIN GENESYS.SI_I_PERSONAS p ON si.id_sjto_impsto = p.id_sjto_impsto
LEFT JOIN GENESYS.DF_S_SUJETOS_ESTADO se ON si.id_sjto_estdo = se.id_sjto_estdo
JOIN GENESYS.DF_C_IMPUESTOS i ON si.id_impsto = i.id_impsto
WHERE s.idntfccion = :nit AND i.cdgo_impsto = 'ICA'
"""

DECLARACIONES_PERIODO_SQL = """
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
"""

EXOGENA_PERIODO_SQL = """
SELECT vgncia_rtncion AS periodo, COALESCE(SUM(vlor_bse), 0) AS ingresos
FROM GENESYS.GI_G_EXOGENA_RETENCIONES
WHERE idntfccion = :nit AND vgncia_rtncion = :periodo
  AND cdgo_exgna_tpo_rgstro = 'RD'
GROUP BY vgncia_rtncion
"""

PARES_METRICAS_SQL = """
SELECT s.idntfccion AS nit, p.nmbre_rzon_scial AS razon_social,
       p.id_actvdad_ecnmca AS ciiu, se.cdgo_sjto_estdo AS regimen,
       NVL(dec_data.base_gravable, 0) AS base_gravable,
       NVL(dec_data.impuesto, 0) AS impuesto,
       NVL(exo_data.ingresos_exogena, 0) AS ingresos_exogena
FROM GENESYS.SI_C_SUJETOS s
JOIN GENESYS.SI_I_SUJETOS_IMPUESTO si ON s.id_sjto = si.id_sjto
JOIN GENESYS.SI_I_PERSONAS p ON si.id_sjto_impsto = p.id_sjto_impsto
LEFT JOIN GENESYS.DF_S_SUJETOS_ESTADO se ON si.id_sjto_estdo = se.id_sjto_estdo
JOIN GENESYS.DF_C_IMPUESTOS i ON si.id_impsto = i.id_impsto
LEFT JOIN (
    SELECT d.id_sjto_impsto,
           SUM(d.bse_grvble) AS base_gravable,
           SUM(d.vlor_ttal) AS impuesto
    FROM GENESYS.GI_G_DECLARACIONES d
    JOIN GENESYS.GI_D_DCLRCNES_VGNCIAS_FRMLR dvf ON d.id_dclrcion_vgncia_frmlrio = dvf.id_dclrcion_vgncia_frmlrio
    JOIN GENESYS.GI_D_FORMULARIOS f ON dvf.id_frmlrio = f.id_frmlrio
    WHERE d.vgncia = :periodo
      AND d.cdgo_dclrcion_estdo = 'PRS'
      AND d.fcha_anlcion IS NULL
      AND f.cdgo_frmlrio LIKE 'FUN%'
    GROUP BY d.id_sjto_impsto
) dec_data ON si.id_sjto_impsto = dec_data.id_sjto_impsto
LEFT JOIN (
    SELECT idntfccion, COALESCE(SUM(vlor_bse), 0) AS ingresos_exogena
    FROM GENESYS.GI_G_EXOGENA_RETENCIONES
    WHERE vgncia_rtncion = :periodo
      AND cdgo_exgna_tpo_rgstro = 'RD'
    GROUP BY idntfccion
) exo_data ON s.idntfccion = exo_data.idntfccion
WHERE i.cdgo_impsto = 'ICA'
  AND p.id_actvdad_ecnmca = :ciiu
  AND (:regimen IS NULL OR se.cdgo_sjto_estdo = :regimen)
ORDER BY s.idntfccion
OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
"""

HISTORICO_DECLARACIONES_SQL = """
SELECT d.vgncia AS periodo,
       SUM(d.bse_grvble) AS base_gravable,
       SUM(d.vlor_ttal) AS impuesto
FROM GENESYS.GI_G_DECLARACIONES d
JOIN GENESYS.GI_D_DCLRCNES_VGNCIAS_FRMLR dvf ON d.id_dclrcion_vgncia_frmlrio = dvf.id_dclrcion_vgncia_frmlrio
JOIN GENESYS.GI_D_FORMULARIOS f ON dvf.id_frmlrio = f.id_frmlrio
WHERE d.id_sjto_impsto = :id_sjto_impsto
  AND d.cdgo_dclrcion_estdo = 'PRS'
  AND d.fcha_anlcion IS NULL
  AND f.cdgo_frmlrio LIKE 'FUN%'
GROUP BY d.vgncia
ORDER BY d.vgncia
"""

HISTORICO_EXOGENA_SQL = """
SELECT vgncia_rtncion AS periodo, COALESCE(SUM(vlor_bse), 0) AS ingresos
FROM GENESYS.GI_G_EXOGENA_RETENCIONES
WHERE idntfccion = :nit
  AND cdgo_exgna_tpo_rgstro = 'RD'
GROUP BY vgncia_rtncion
ORDER BY vgncia_rtncion
"""


class OracleBehavioralRepository:
    def __init__(self, client: OracleClient | None = None):
        self.client = client or OracleClient()

    async def obtener_contribuyente(self, contribuyente_nit: str, periodo: str) -> dict | None:
        contribuyente = await self.client.execute_sql(CONTRIBUYENTE_LOOKUP_SQL, {"nit": contribuyente_nit})
        if not contribuyente:
            return None

        row = contribuyente[0] if isinstance(contribuyente, list) else contribuyente
        id_sjto_impsto = row.get("id_sjto_impsto")

        base_gravable = 0.0
        impuesto = 0.0
        if id_sjto_impsto:
            declaraciones = await self.client.execute_sql(
                DECLARACIONES_PERIODO_SQL,
                {"id_sjto_impsto": id_sjto_impsto, "periodo": periodo},
            )
            if declaraciones:
                items = declaraciones if isinstance(declaraciones, list) else [declaraciones]
                base_gravable = sum(float(d.get("base_gravable", 0) or 0) for d in items)
                impuesto = sum(float(d.get("impuesto", 0) or 0) for d in items)

        ingresos_exogena = 0.0
        exogena = await self.client.execute_sql(
            EXOGENA_PERIODO_SQL,
            {"nit": contribuyente_nit, "periodo": periodo},
        )
        if exogena:
            items = exogena if isinstance(exogena, list) else [exogena]
            ingresos_exogena = sum(float(e.get("ingresos", 0) or 0) for e in items)

        return {
            "contribuyente_nit": row.get("nit", contribuyente_nit),
            "razon_social": row.get("razon_social", ""),
            "ciiu": str(row.get("ciiu", "") or ""),
            "regimen": row.get("regimen", ""),
            "base_gravable": base_gravable,
            "impuesto": impuesto,
            "ingresos_exogena": ingresos_exogena,
        }

    async def obtener_historico_nit(self, contribuyente_nit: str) -> list[dict]:
        contribuyente = await self.client.execute_sql(CONTRIBUYENTE_LOOKUP_SQL, {"nit": contribuyente_nit})
        if not contribuyente:
            return []

        row = contribuyente[0] if isinstance(contribuyente, list) else contribuyente
        id_sjto_impsto = row.get("id_sjto_impsto")
        if not id_sjto_impsto:
            return []

        declaraciones_all = await self.client.execute_sql(
            HISTORICO_DECLARACIONES_SQL,
            {"id_sjto_impsto": id_sjto_impsto},
        )
        exogena_all = await self.client.execute_sql(
            HISTORICO_EXOGENA_SQL,
            {"nit": contribuyente_nit},
        )

        dec_map = {}
        if declaraciones_all:
            items = declaraciones_all if isinstance(declaraciones_all, list) else [declaraciones_all]
            for d in items:
                dec_map[d["periodo"]] = d

        exo_map = {}
        if exogena_all:
            items = exogena_all if isinstance(exogena_all, list) else [exogena_all]
            for e in items:
                exo_map[e["periodo"]] = e

        all_periodos = sorted(set(list(dec_map.keys()) + list(exo_map.keys())))

        result = []
        for periodo in all_periodos:
            d = dec_map.get(periodo, {})
            e = exo_map.get(periodo, {})
            result.append({
                "periodo": periodo,
                "base_gravable": float(d.get("base_gravable", 0) or 0),
                "impuesto": float(d.get("impuesto", 0) or 0),
                "ingresos_exogena": float(e.get("ingresos", 0) or 0),
            })

        return result

    async def obtener_pares(
        self,
        periodo: str,
        ciiu: str,
        regimen: str | None,
        page_size: int = 500,
        max_rows: int = 2000,
    ) -> list[dict]:
        rows: list[dict] = []
        offset = 0
        while len(rows) < max_rows:
            limit = min(page_size, max_rows - len(rows))
            result = await self.client.execute_sql(
                PARES_METRICAS_SQL,
                {"periodo": periodo, "ciiu": ciiu, "regimen": regimen, "offset": offset, "limit": limit},
            )
            if not result:
                break
            items = result if isinstance(result, list) else [result]
            rows.extend(items)
            if len(items) < limit:
                break
            offset += limit
        return rows
