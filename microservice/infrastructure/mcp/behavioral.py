from __future__ import annotations

from infrastructure.mcp.oracle_adapter import OracleClient

CONTRIBUYENTE_METRICAS_SQL = """
SELECT c.nit,
       c.razon_social,
       c.ciiu,
       c.regimen,
       NVL(d.base_gravable, 0) AS base_gravable,
       NVL(d.impuesto, 0) AS impuesto,
       NVL(e.ingresos_exogena, 0) AS ingresos_exogena
FROM contribuyentes c
LEFT JOIN (
    SELECT nit, SUM(base_gravable) AS base_gravable, SUM(impuesto) AS impuesto
    FROM declaraciones_ica
    WHERE periodo = :periodo
    GROUP BY nit
) d ON d.nit = c.nit
LEFT JOIN (
    SELECT nit, SUM(ingresos) AS ingresos_exogena
    FROM exogena_dian
    WHERE periodo = :periodo
    GROUP BY nit
) e ON e.nit = c.nit
WHERE c.nit = :nit
"""


PARES_METRICAS_SQL = """
SELECT c.nit,
       c.razon_social,
       c.ciiu,
       c.regimen,
       NVL(d.base_gravable, 0) AS base_gravable,
       NVL(d.impuesto, 0) AS impuesto,
       NVL(e.ingresos_exogena, 0) AS ingresos_exogena
FROM contribuyentes c
LEFT JOIN (
    SELECT nit, SUM(base_gravable) AS base_gravable, SUM(impuesto) AS impuesto
    FROM declaraciones_ica
    WHERE periodo = :periodo
    GROUP BY nit
) d ON d.nit = c.nit
LEFT JOIN (
    SELECT nit, SUM(ingresos) AS ingresos_exogena
    FROM exogena_dian
    WHERE periodo = :periodo
    GROUP BY nit
) e ON e.nit = c.nit
WHERE c.ciiu = :ciiu
  AND (:regimen IS NULL OR c.regimen = :regimen)
ORDER BY c.nit
OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
"""


HISTORICO_NIT_SQL = """
SELECT COALESCE(d.periodo, e.periodo) AS periodo,
       NVL(d.base_gravable, 0) AS base_gravable,
       NVL(d.impuesto, 0) AS impuesto,
       NVL(e.ingresos_exogena, 0) AS ingresos_exogena
FROM (
    SELECT periodo, SUM(base_gravable) AS base_gravable, SUM(impuesto) AS impuesto
    FROM declaraciones_ica WHERE nit = :nit GROUP BY periodo
) d
FULL OUTER JOIN (
    SELECT periodo, SUM(ingresos) AS ingresos_exogena
    FROM exogena_dian WHERE nit = :nit GROUP BY periodo
) e ON d.periodo = e.periodo
ORDER BY periodo
"""


class OracleBehavioralRepository:
    def __init__(self, client: OracleClient | None = None):
        self.client = client or OracleClient()

    async def obtener_contribuyente(self, nit: str, periodo: str) -> dict | None:
        result = await self.client.execute_sql(CONTRIBUYENTE_METRICAS_SQL, {"nit": nit, "periodo": periodo})
        if not result:
            return None
        return result[0]

    async def obtener_historico_nit(self, nit: str) -> list[dict]:
        result = await self.client.execute_sql(HISTORICO_NIT_SQL, {"nit": nit})
        if not result:
            return []
        return result if isinstance(result, list) else [result]

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
