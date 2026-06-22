def nivel_riesgo(srf: float) -> str:
    if srf >= 70:
        return "ALTO"
    if srf >= 40:
        return "MEDIO"
    return "BAJO"
