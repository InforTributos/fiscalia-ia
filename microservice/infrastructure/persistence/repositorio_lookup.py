import logging

from domain.ports.lookup_repository import (
    AtributosICA,
    ConfiguracionDeclaracion,
    LookupRepository,
    ProgramaInfo,
)
from infrastructure.mcp.oracle_adapter import OracleClient

logger = logging.getLogger(__name__)


class RepositorioLookupOracle(LookupRepository):
    def __init__(self, client: OracleClient):
        self._client = client
        self._cache_impuesto: dict[str, int] = {}
        self._cache_programa: dict[str, int] = {}
        self._cache_config: ConfiguracionDeclaracion | None = None
        self._cache_atributos: dict[str, AtributosICA] = {}

    async def get_impuesto_id(self, cdgo_impsto: str) -> int:
        if cdgo_impsto not in self._cache_impuesto:
            result = await self._client.execute_sql(
                "SELECT id_impsto FROM DF_C_IMPUESTOS WHERE cdgo_impsto = :cdgo",
                {"cdgo": cdgo_impsto},
            )
            if not result:
                raise ValueError(f"Impuesto '{cdgo_impsto}' no encontrado en DF_C_IMPUESTOS")
            self._cache_impuesto[cdgo_impsto] = result[0]["id_impsto"]
            logger.info("Lookup: impuesto %s = id %d", cdgo_impsto, result[0]["id_impsto"])
        return self._cache_impuesto[cdgo_impsto]

    async def get_programa_id(self, cdgo_prgrma: str) -> int:
        if cdgo_prgrma not in self._cache_programa:
            result = await self._client.execute_sql(
                "SELECT id_prgrma FROM FI_D_PROGRAMAS WHERE cdgo_prgrma = :cdgo",
                {"cdgo": cdgo_prgrma},
            )
            if not result:
                raise ValueError(f"Programa '{cdgo_prgrma}' no encontrado en FI_D_PROGRAMAS")
            self._cache_programa[cdgo_prgrma] = result[0]["id_prgrma"]
            logger.info("Lookup: programa %s = id %d", cdgo_prgrma, result[0]["id_prgrma"])
        return self._cache_programa[cdgo_prgrma]

    async def get_programas_por_impuesto(
        self, id_impsto: int, cdgos_prgrma: list[str] | None = None,
    ) -> list[ProgramaInfo]:
        if cdgos_prgrma:
            placeholders = ", ".join(f":c{i}" for i in range(len(cdgos_prgrma)))
            sql = f"""
                SELECT DISTINCT p.id_prgrma, p.cdgo_prgrma, p.nmbre_prgrma
                FROM FI_D_PROGRAMAS p
                JOIN FI_D_PROGRAMAS_IMPUESTO pi ON p.id_prgrma = pi.id_prgrma
                WHERE pi.id_impsto = :id_impsto
                  AND p.cdgo_prgrma IN ({placeholders})
                  AND p.actvo = 'S'
            """
            params = {"id_impsto": id_impsto}
            params.update({f"c{i}": c for i, c in enumerate(cdgos_prgrma)})
        else:
            sql = """
                SELECT DISTINCT p.id_prgrma, p.cdgo_prgrma, p.nmbre_prgrma
                FROM FI_D_PROGRAMAS p
                JOIN FI_D_PROGRAMAS_IMPUESTO pi ON p.id_prgrma = pi.id_prgrma
                WHERE pi.id_impsto = :id_impsto
                  AND p.actvo = 'S'
            """
            params = {"id_impsto": id_impsto}

        rows = await self._client.execute_sql(sql, params)
        return [
            ProgramaInfo(
                id_prgrma=r["id_prgrma"],
                cdgo_prgrma=r["cdgo_prgrma"],
                nmbre_prgrma=r["nmbre_prgrma"],
            ) for r in (rows or [])
        ]

    async def get_configuracion_declaracion(self) -> ConfiguracionDeclaracion:
        if self._cache_config is not None:
            return self._cache_config

        result = await self._client.execute_sql(
            "SELECT cdgo_clnte, ind_prsntcion_dclrcion FROM GI_D_DCLRCN_PRSNTCN_CONFGRCN WHERE ROWNUM <= 1",
        )
        if not result:
            raise ValueError("No se encontró configuración de declaración en GI_D_DCLRCN_PRSNTCN_CONFGRCN")

        cfg = result[0]
        self._cache_config = ConfiguracionDeclaracion(
            cdgo_clnte=cfg["cdgo_clnte"],
            ind_prsntcion_dclrcion=cfg["ind_prsntcion_dclrcion"],
        )
        logger.info(
            "Lookup: config declaracion = %s (cliente %d)",
            self._cache_config.ind_prsntcion_dclrcion,
            self._cache_config.cdgo_clnte,
        )
        return self._cache_config

    async def get_atributos_ica(self, periodo: str, tipo_formulario: str = "FUN") -> AtributosICA:
        cache_key = f"{periodo}:{tipo_formulario}"
        if cache_key in self._cache_atributos:
            return self._cache_atributos[cache_key]

        id_impsto = await self.get_impuesto_id("ICA")
        vigencia = int(periodo)

        forms = await self._client.execute_sql(
            """
            SELECT DISTINCT frm.id_frmlrio, frm.cdgo_frmlrio
            FROM GI_G_DECLARACIONES decl
            JOIN GI_D_DCLRCNES_VGNCIAS_FRMLR dvf
                ON decl.id_dclrcion_vgncia_frmlrio = dvf.id_dclrcion_vgncia_frmlrio
            JOIN GI_D_FORMULARIOS frm ON dvf.id_frmlrio = frm.id_frmlrio
            WHERE decl.id_impsto = :id_impsto
              AND decl.vgncia = :vigencia
              AND frm.cdgo_frmlrio LIKE :tipo_pattern
              AND ROWNUM <= 10
            """,
            {"id_impsto": id_impsto, "vigencia": vigencia, "tipo_pattern": f"{tipo_formulario}%"},
        )

        if not forms:
            raise ValueError(
                f"No se encontraron formularios tipo '{tipo_formulario}' para ICA en período {periodo}"
            )

        form_ids = [f["id_frmlrio"] for f in forms]
        logger.info(
            "Lookup: %d formularios '%s' encontrados para período %s: %s",
            len(form_ids), tipo_formulario, periodo, [f["cdgo_frmlrio"] for f in forms],
        )

        placeholders = ", ".join(f":f{i}" for i in range(len(form_ids)))
        params = {f"f{i}": fid for i, fid in enumerate(form_ids)}

        attributes = await self._client.execute_sql(
            f"""
            SELECT atrbto.id_frmlrio_rgion_atrbto, atrbto.nmbre_dsplay,
                   atrbto.cdgo_atrbto_tpo, rg.dscrpcion AS region_dscrpcion
            FROM GI_D_FRMLRIOS_RGION_ATRBTO atrbto
            JOIN GI_D_FORMULARIOS_REGION rg ON atrbto.id_frmlrio_rgion = rg.id_frmlrio_rgion
            WHERE rg.id_frmlrio IN ({placeholders})
            """,
            params,
        )

        if not attributes:
            raise ValueError(f"No se encontraron atributos para formularios ICA en período {periodo}")

        ciiu_ids = []
        tarifa_ids = []
        ret_recibidas_ids = []
        ret_practicadas_ids = []

        for attr in attributes:
            name = (attr.get("nmbre_dsplay") or "").strip()
            atype = attr.get("cdgo_atrbto_tpo") or ""
            aid = attr["id_frmlrio_rgion_atrbto"]

            if name == "CODIGO CIIU" and atype == "SLQ":
                ciiu_ids.append(aid)
            elif name.upper().startswith("TARIFA") and atype in ("TXT", "NUM", "SLQ"):
                tarifa_ids.append(aid)
            elif "RETENCION" in name.upper() or "AUTORRETENCION" in name.upper():
                upper_name = name.upper()
                if "AUTORRETENCION" in upper_name:
                    ret_practicadas_ids.append(aid)
                elif "QUE LE PRACTICARON" in upper_name or "LE PRACTICARON" in upper_name:
                    ret_recibidas_ids.append(aid)
                elif "PRACTICAD" in upper_name:
                    ret_practicadas_ids.append(aid)
                else:
                    ret_recibidas_ids.append(aid)

        if not ciiu_ids:
            logger.warning("No se encontraron atributos CIIU (CODIGO CIIU, SLQ) en período %s", periodo)
        if not tarifa_ids:
            logger.warning("No se encontraron atributos TARIFA en período %s", periodo)

        result = AtributosICA(
            ciiu_ids=ciiu_ids,
            tarifa_ids=tarifa_ids,
            ret_recibidas_ids=ret_recibidas_ids,
            ret_practicadas_ids=ret_practicadas_ids,
        )

        logger.info(
            "Lookup ICA (%s): CIIU=%s TARIFA=%s RET_RECIBIDAS=%s RET_PRACTICADAS=%s",
            tipo_formulario, ciiu_ids, tarifa_ids, ret_recibidas_ids, ret_practicadas_ids,
        )

        self._cache_atributos[cache_key] = result
        return result
