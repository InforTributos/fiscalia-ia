from dataclasses import dataclass


@dataclass(frozen=True)
class NIT:
    valor: str

    def __post_init__(self):
        if not self.valor or not self.valor.strip():
            raise ValueError("NIT no puede estar vacío")
        limpio = self.valor.replace("-", "").replace(".", "").strip()
        if not limpio.isdigit():
            raise ValueError(f"NIT inválido: {self.valor}")

    def formateado(self) -> str:
        return self.valor.strip()
