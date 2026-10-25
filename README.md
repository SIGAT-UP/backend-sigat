# backend-sigat

API del sistema de monitoreo fitosanitario del durazno (ICA). Monolito modular
en Python + FastAPI. Este repositorio contiene solo código y su capa de
despliegue; los documentos de arquitectura viven fuera (ADR-16).

## Estructura

```text
src/ica_api/
├── main.py                 composición de la aplicación
├── api/
│   ├── deps.py             dependencias compartidas
│   ├── errors.py           formato único de error
│   └── v1/
│       ├── router.py       composición de routers de módulos
│       └── routes/
├── core/                   config, logging, paginación, time, security
├── modules/                un módulo de negocio por carpeta
│   ├── identidad/
│   ├── sincronizacion/
│   ├── registro/
│   ├── configuracion/
│   ├── imagenes/
│   ├── concepto/
│   ├── reportes/
│   ├── administracion/
│   ├── importacion/
│   ├── laboratorio/
│   └── calidad/
├── infra/                  db, queue, storage, geo, observability
└── kernel/                 primitivas compartidas
```

Cada módulo repite la misma anatomía:

```text
modules/registro/
├── domain/                 entidades, value objects, servicios, eventos, puertos
├── application/            casos de uso, DTO, handlers
├── infrastructure/         persistencia, geo, mensajería
├── api/                    router y esquemas HTTP
└── tests/
```

Regla de dependencia:

```text
api → application → domain
infrastructure → application/domain
domain → nada (ni FastAPI, ni SQLAlchemy, ni PostGIS)
```

## Endpoints

| Ruta | Uso |
|---|---|
| `GET /` | Identificación del servicio |
| `GET /health/live` | Liveness; lo usa Coolify |
| `GET /health/ready` | Readiness; verifica PostgreSQL |
| `GET /api/v1/version` | Versión de la API |
| `GET /docs` | Swagger |

## Desarrollo local

```bash
uv sync
cp .env.example .env
uv run uvicorn ica_api.main:app --reload --port 8000
```

Calidad:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
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

## Contrato

```bash
uv run python -m scripts.export_openapi
```

Escribe `contracts/openapi.json`. Ese archivo es el único artefacto que cruza a
los repositorios de la web y del móvil; no se edita a mano.

## Docker

```bash
docker build -t sigat-api .
docker run --rm -p 8000:8000 --env-file .env sigat-api
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
