from __future__ import annotations

from infrastructure.mcp.oracle_adapter import OracleClient

TARGET_SQL = """
SELECT s.idntfccion AS nit, p.nmbre_rzon_scial AS razon_social,
       p.id_actvdad_ecnmca AS ciiu, se.cdgo_sjto_estdo AS regimen,
       s.drccion, c.tlfno, c.email
FROM GENESYS.SI_C_SUJETOS s
JOIN GENESYS.SI_I_SUJETOS_IMPUESTO si ON s.id_sjto = si.id_sjto
JOIN GENESYS.SI_I_PERSONAS p ON si.id_sjto_impsto = p.id_sjto_impsto
LEFT JOIN GENESYS.DF_S_SUJETOS_ESTADO se ON si.id_sjto_estdo = se.id_sjto_estdo
LEFT JOIN GENESYS.DF_S_CLIENTES c ON s.cdgo_clnte = c.cdgo_clnte
JOIN GENESYS.DF_C_IMPUESTOS i ON si.id_impsto = i.id_impsto
WHERE s.idntfccion = :nit AND i.cdgo_impsto = 'ICA'
"""

RELACIONADOS_SQL_TEMPLATE = """
SELECT s.idntfccion AS nit, p.nmbre_rzon_scial AS razon_social,
       p.id_actvdad_ecnmca AS ciiu, se.cdgo_sjto_estdo AS regimen,
       s.drccion, c.tlfno, c.email
FROM GENESYS.SI_C_SUJETOS s
JOIN GENESYS.SI_I_SUJETOS_IMPUESTO si ON s.id_sjto = si.id_sjto
JOIN GENESYS.SI_I_PERSONAS p ON si.id_sjto_impsto = p.id_sjto_impsto
LEFT JOIN GENESYS.DF_S_SUJETOS_ESTADO se ON si.id_sjto_estdo = se.id_sjto_estdo
LEFT JOIN GENESYS.DF_S_CLIENTES c ON s.cdgo_clnte = c.cdgo_clnte
JOIN GENESYS.DF_C_IMPUESTOS i ON si.id_impsto = i.id_impsto
WHERE i.cdgo_impsto = 'ICA'
  AND {columna_calificada} = :valor
  AND s.idntfccion <> :nit
ORDER BY s.idntfccion
OFFSET 0 ROWS FETCH NEXT :limit ROWS ONLY
"""

COLUMN_PREFIX_MAP: dict[str, str] = {
    "tlfno": "c",
    "email": "c",
}

ATTRIBUTE_COLUMNS = {
    "representante": ("representante_legal", "representante", "id_representante"),
    "direccion": ("drccion", "direccion_principal", "direccion"),
    "telefono": ("tlfno", "telefono_principal", "celular", "telefono"),
    "correo": ("email", "correo_electronico", "correo"),
}


class OracleGraphRepository:
    def __init__(self, client: OracleClient | None = None):
        self.client = client or OracleClient()

    async def obtener_contribuyente(self, contribuyente_nit: str) -> dict | None:
        rows = await self.client.execute_sql(TARGET_SQL, {"nit": contribuyente_nit})
        if not rows:
            return None
        return _normalizar_atributos(rows[0])

    async def obtener_relacionados(self, contribuyente: dict, limit: int = 25) -> dict[str, list[dict]]:
        relacionados: dict[str, list[dict]] = {}
        for atributo, columnas in ATTRIBUTE_COLUMNS.items():
            columna = _resolver_columna(contribuyente, columnas)
            if not columna:
                relacionados[atributo] = []
                continue
            valor = contribuyente.get(atributo)
            if not valor:
                relacionados[atributo] = []
                continue
            prefix = COLUMN_PREFIX_MAP.get(columna, "s")
            columna_calificada = f"{prefix}.{columna}"
            sql = RELACIONADOS_SQL_TEMPLATE.format(columna_calificada=columna_calificada)
            rows = await self.client.execute_sql(sql, {
                "valor": valor,
                "nit": contribuyente.get("contribuyente_nit", ""),
                "limit": limit,
            })
            items = rows if isinstance(rows, list) else [rows]
            relacionados[atributo] = [_normalizar_atributos(row) for row in items]
        return relacionados


def _resolver_columna(row: dict, columnas: tuple[str, ...]) -> str | None:
    for columna in columnas:
        if columna in row and row.get(columna):
            return columna
    return None


def _normalizar_atributos(row: dict) -> dict:
    normalized = dict(row)
    for atributo, columnas in ATTRIBUTE_COLUMNS.items():
        for columna in columnas:
            if columna in row and row.get(columna):
                normalized[atributo] = row.get(columna)
                break
    return normalized
