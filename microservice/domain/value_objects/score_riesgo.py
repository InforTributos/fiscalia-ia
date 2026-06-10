from dataclasses import dataclass


@dataclass(frozen=True)
class ScoreRiesgo:
    valor: float

    def __post_init__(self):
        if not (0 <= self.valor <= 100):
            raise ValueError(f"Score debe estar entre 0 y 100: {self.valor}")

    @property
    def nivel(self) -> str:
        if self.valor >= 70:
            return "ALTO"
        if self.valor >= 40:
            return "MEDIO"
        return "BAJO"
