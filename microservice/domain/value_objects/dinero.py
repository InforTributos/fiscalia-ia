from dataclasses import dataclass


@dataclass(frozen=True)
class Dinero:
    valor: float

    def __post_init__(self):
        if self.valor < 0:
            raise ValueError(f"Monto no puede ser negativo: {self.valor}")

    def __add__(self, otro: "Dinero") -> "Dinero":
        return Dinero(self.valor + otro.valor)

    def __sub__(self, otro: "Dinero") -> "Dinero":
        return Dinero(self.valor - otro.valor)

    def __repr__(self) -> str:
        return f"${self.valor:,.0f}"
