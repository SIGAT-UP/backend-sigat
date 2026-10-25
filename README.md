# backend-sigat

API del sistema de monitoreo fitosanitario del durazno (ICA). Monolito modular
en Python + FastAPI. Este repositorio contiene solo código y su capa de
despliegue; los documentos de arquitectura viven fuera (ADR-16).

## Estado

Esqueleto inicial: aplicación FastAPI, endpoints de salud, configuración por
variables de entorno y migraciones preparadas. Los módulos de dominio
(`identidad`, `registro`, `sincronizacion`, ...) se agregan dentro de
`src/ica_api/modules/`.

## Endpoints

| Ruta | Uso |
|---|---|
| `GET /` | Identificación del servicio |
| `GET /health/live` | Liveness; lo usa Coolify |
| `GET /health/ready` | Readiness; verifica PostgreSQL |
| `GET /docs` | Swagger |

## Desarrollo local

```bash
uv sync
cp .env.example .env
uv run uvicorn ica_api.main:app --reload --port 8000
```

Pruebas y estilo:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Variables de entorno

| Variable | Obligatoria | Ejemplo |
|---|---|---|
| `DATABASE_URL` | Sí | `postgresql+psycopg://ica:clave@db:5432/ica` |
| `JWT_SECRET` | Sí | valor largo y aleatorio |
| `JWT_ALGORITHM` | No | `HS256` |
| `CORS_ORIGINS` | Sí | `https://app.tudominio.com` |
| `ENV` | No | `production` |
| `RUN_MIGRATIONS` | No | `0` |

## Docker

```bash
docker build -t ica-api .
docker run --rm -p 8000:8000 --env-file .env ica-api
curl -i http://localhost:8000/health/live
```

La imagen escucha en `0.0.0.0:8000`; ese es el valor de *Exposed ports* en
Coolify.

## Migraciones

```bash
uv run alembic revision --autogenerate -m "descripcion"
uv run alembic upgrade head
```

En producción se ejecuta `alembic upgrade head` una vez por release desde la
terminal de Coolify. `RUN_MIGRATIONS=1` existe para local o para una única
instancia, no para producción con varios contenedores.

## Despliegue en Coolify

1. Recurso de tipo Git con `Build Pack = Dockerfile`.
2. *Exposed ports*: `8000`.
3. Variables de entorno: las de la tabla anterior.
4. *Healthcheck*: `GET /health/live`, puerto `8000`.
5. Dominio `https` con certificado.
