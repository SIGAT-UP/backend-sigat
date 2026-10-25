# syntax=docker/dockerfile:1
#
# ica-durazno-api · imagen de producción
# Base Alpine (musl) para mantener la imagen pequeña.
#
# Requisitos del contexto de build:
#   pyproject.toml   (obligatorio)
#   uv.lock          (recomendado: build reproducible; si no existe se resuelve en el build)
#   src/ica_api/     (paquete de la aplicación)
#   docker/entrypoint.sh
#
# Si más adelante se agregan dependencias geoespaciales con ruedas solo
# manylinux (shapely, pyproj, geopandas), cambiar la base a python:3.12-slim:
# en musl esas ruedas no existen y el build intentaría compilar desde fuente.

# ---------- etapa 1: dependencias y bytecode ----------
FROM python:3.12-alpine AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
# Fijar la etiqueta (por ejemplo uv:0.9) en el primer release reproducible.

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# libpq-dev y build-base solo hacen falta para compilar psycopg si no hay rueda musl.
RUN apk add --no-cache build-base libpq-dev

COPY . .

# Si hay uv.lock se usa congelado (reproducible); si no, se resuelve en el build.
RUN if [ -f uv.lock ]; then \
      uv sync --frozen --no-dev; \
    else \
      uv sync --no-dev; \
    fi

# ---------- etapa 2: runtime ----------
FROM python:3.12-alpine AS runtime

RUN apk add --no-cache libpq tzdata \
 && addgroup -S app \
 && adduser -S -G app -h /app app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=America/Bogota

WORKDIR /app

COPY --from=builder --chown=app:app /app /app
RUN chmod +x /app/docker/entrypoint.sh

USER app

EXPOSE 8000

# Coolify puede usar su propio healthcheck; este sirve para docker run local.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8000/health/live >/dev/null || exit 1

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["uvicorn", "ica_api.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]
