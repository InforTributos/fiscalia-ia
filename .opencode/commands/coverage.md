---
description: Ejecutar tests con reporte de cobertura
---

PYTHONPATH=microservice pytest tests/unit/ --cov=microservice --cov-report=term --cov-fail-under=80
