from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class AtributosICA:
    ciiu_ids: list[int] = field(default_factory=list)
    tarifa_ids: list[int] = field(default_factory=list)
    ret_recibidas_ids: list[int] = field(default_factory=list)
    ret_practicadas_ids: list[int] = field(default_factory=list)


@dataclass
class ProgramaInfo:
    id_prgrma: int
    cdgo_prgrma: str
    nmbre_prgrma: str


@dataclass
class ConfiguracionDeclaracion:
    ind_prsntcion_dclrcion: str  # 'A' = cartera al autorizar, 'R' = cartera al recaudar
    cdgo_clnte: int


class LookupRepository(ABC):
    @abstractmethod
    async def get_impuesto_id(self, cdgo_impsto: str) -> int:
        ...

    @abstractmethod
    async def get_programa_id(self, cdgo_prgrma: str) -> int:
        ...

    @abstractmethod
    async def get_programas_por_impuesto(
        self, id_impsto: int, cdgos_prgrma: list[str] | None = None,
    ) -> list[ProgramaInfo]:
        ...

    @abstractmethod
    async def get_configuracion_declaracion(self) -> ConfiguracionDeclaracion:
        ...

    @abstractmethod
    async def get_atributos_ica(self, periodo: str, tipo_formulario: str = "FUN") -> AtributosICA:
        ...
