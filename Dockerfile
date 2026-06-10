FROM python:3.11-slim AS builder

WORKDIR /build
COPY microservice/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /install /usr/local

COPY microservice/ ./microservice/
COPY docs/ ./docs/
COPY db/ ./db/

RUN adduser --disabled-password --no-create-home --uid 1000 fiscalia

USER fiscalia

EXPOSE 8000

CMD ["uvicorn", "microservice.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
