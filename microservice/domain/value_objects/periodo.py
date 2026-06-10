from dataclasses import dataclass


@dataclass(frozen=True)
class Periodo:
    valor: str

    def __post_init__(self):
        if not self.valor or len(self.valor) < 7:
            raise ValueError(f"Período inválido: {self.valor}. Formato esperado: YYYY-MM")

    @property
    def year(self) -> str:
        return self.valor[:4]

    @property
    def month(self) -> str:
        return self.valor[5:7]
