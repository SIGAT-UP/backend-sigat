# syntax=docker/dockerfile:1.7
# Una sola imagen para los dos procesos del mismo despliegue (ADR-14):
#   api    -> uvicorn sigat_api.main:app
#   worker -> python -m sigat_api.worker   (reproceso de MTD y concepto)
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends libgeos-c1v5 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app

FROM base AS deps
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --upgrade pip && pip install .

FROM base AS runtime
RUN useradd --create-home --uid 10001 sigat
COPY --from=deps /usr/local /usr/local
COPY alembic.ini ./
COPY migrations ./migrations
COPY bd ./bd
USER sigat
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/salud'); sys.exit(0)"
CMD ["uvicorn", "sigat_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
