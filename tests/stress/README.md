# Stress Testing — FiscalIA

## Requisitos

```bash
pip install locust httpx
```

## Tests Funcionales (httpx contra API real)

```bash
PYTHONPATH=microservice pytest tests/functional/ -v
```

## Load Testing (GUI)

```bash
locust -f tests/stress/locustfile.py --host=http://localhost:8000
# Abrir http://localhost:8089
```

## Load Testing (Headless)

```bash
# 50 usuarios, 5/s de spawn, 5 minutos
locust -f tests/stress/locustfile.py --host=http://localhost:8000 --headless -u 50 -r 5 --run-time 5m --csv=reports/stress
```

## Stress Tests

```bash
# Rate limit saturation
locust -f tests/stress/locustfile_stress.py --host=http://localhost:8000 --headless -u 50 -r 10 --run-time 3m --csv=reports/stress_rate

# Procesos concurrentes
locust -f tests/stress/locustfile_stress.py --host=http://localhost:8000 --headless -u 20 -r 5 --run-time 3m --csv=reports/stress_proceso

# Lectura pesada
locust -f tests/stress/locustfile_stress.py --host=http://localhost:8000 --headless -u 100 -r 20 --run-time 5m --csv=reports/stress_read
```

## Reportes

Los CSV se generan en `reports/stress_*.csv`. Se pueden analizar con:

```python
import pandas as pd
df = pd.read_csv("reports/stress_stats.csv")
print(df.describe())
```

## Escenarios

| Archivo | Usuarios | Objetivo |
|---|---|---|
| `locustfile.py` | 1-50 | Carga mixta realista (6 perfiles) |
| `locustfile_stress.py` | 20-100 | Stress puro por escenario |
