---
description: Analizar un NIT específico con el servicio local
---

curl -s -X POST "http://localhost:8000/api/v1/analizar/$1" \
  -H "Content-Type: application/json" \
  -d "{\\"entidad_nit\\": \"9003189639\", \"nit_objetivo\": \"$1\", \"periodo\": \"2024\"}" \
  | python -m json.tool
