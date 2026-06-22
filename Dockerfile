FROM python:3.11-slim AS builder

WORKDIR /build
COPY microservice/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /install /usr/local

COPY microservice/ ./microservice/

RUN adduser --disabled-password --no-create-home --uid 1000 fiscalia

USER fiscalia

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

CMD ["uvicorn", "microservice.main:app", "--host", "0.0.0.0", "--port", "8000"]
