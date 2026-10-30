"""Punto de entrada HTTP: ``uvicorn sigat_api.main:app``."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from sigat_api import __version__
from sigat_api.api.errores import registrar_manejadores
from sigat_api.api.middleware import registrar_middleware
from sigat_api.api.v1.router import router_v1
from sigat_api.config import obtener_configuracion
from sigat_api.infra.db.motor import cerrar_motor, crear_motor
from sigat_api.infra.observabilidad.logs import configurar_logs

DESCRIPCION = """
Backend ÚNICO para la **web SIGAT** (agrónomo, administrador, productor) y la **app móvil**
(técnico, productor, agrónomo). Base de datos SIGAT v9 (PostgreSQL 16 + PostGIS).

* Autenticación: `Authorization: Bearer <token>` (ver `/auth/login`).
* Errores: `application/problem+json` (RFC 9457) con `codigo` estable.
* Fechas: ISO 8601 con zona; fechas sin hora `AAAA-MM-DD`; números con punto decimal.
* Captura de campo: `POST /sincronizacion/lotes` (operaciones idempotentes, resultado por operación).
"""


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
    cfg = obtener_configuracion()
    crear_motor(cfg)
    yield
    await cerrar_motor()


def crear_app() -> FastAPI:
    cfg = obtener_configuracion()
    configurar_logs(cfg)
    app = FastAPI(
        title="sigat-durazno-api",
        version=__version__,
        description=DESCRIPCION,
        default_response_class=ORJSONResponse,
        lifespan=ciclo_de_vida,
        openapi_url=f"{cfg.prefijo_api}/openapi.json",
        docs_url=f"{cfg.prefijo_api}/docs" if cfg.entorno != "produccion" else None,
        redoc_url=None,
    )
    registrar_middleware(app, cfg)
    registrar_manejadores(app)
    app.include_router(router_v1, prefix=cfg.prefijo_api)
    return app


app = crear_app()
