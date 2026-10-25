"""Punto de entrada de la API.

Expone la aplicación FastAPI y los dos endpoints de salud:
  /health/live  -> el proceso está vivo (lo usa Coolify)
  /health/ready -> la API puede atender: verifica la base de datos
"""

from functools import lru_cache

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from ica_api.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 2},
    )


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="ICA Durazno API",
        version="0.1.0",
        description="Sistema de monitoreo fitosanitario del durazno. Uso interno del ICA.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", tags=["salud"])
    def root() -> dict[str, str]:
        return {
            "servicio": "ica-durazno-api",
            "version": app.version,
            "entorno": settings.env,
            "docs": "/docs",
        }

    @app.get("/health/live", tags=["salud"])
    def live() -> dict[str, str]:
        """Vivo: no toca dependencias externas."""
        return {"status": "ok"}

    @app.get("/health/ready", tags=["salud"])
    def ready(response: Response) -> dict[str, str]:
        """Listo: comprueba que la base de datos responde."""
        try:
            with get_engine().connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception as exc:  # noqa: BLE001 - el detalle va al log, no al cliente
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"status": "degraded", "database": "unavailable", "detail": type(exc).__name__}
        return {"status": "ok", "database": "ok"}

    return app


app = create_app()
