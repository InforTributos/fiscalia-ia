from __future__ import annotations

from infrastructure.mcp.oracle_adapter import OracleClient

TARGET_SQL = "SELECT * FROM contribuyentes WHERE nit = :nit"

ATTRIBUTE_COLUMNS = {
    "representante": ("representante_legal", "representante", "id_representante"),
    "direccion": ("direccion", "direccion_principal", "drccion"),
    "telefono": ("telefono", "telefono_principal", "celular"),
    "correo": ("correo", "email", "correo_electronico"),
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
            sql = f"""
            SELECT *
            FROM contribuyentes
            WHERE {columna} = :valor
              AND nit <> :nit
            ORDER BY nit
            OFFSET 0 ROWS
            FETCH NEXT :limit ROWS ONLY
            """
            rows = await self.client.execute_sql(sql, {
                "valor": valor,
                "nit": contribuyente.get("contribuyente_nit", ""),
                "limit": limit,
            })
            relacionados[atributo] = [_normalizar_atributos(row) for row in rows]
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
