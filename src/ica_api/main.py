"""Punto de entrada de la API.

Expone la aplicación FastAPI y los dos endpoints de salud:
  /health/live  -> el proceso está vivo (lo usa Coolify)
  /health/ready -> la API puede atender: verifica la base de datos
"""

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from ica_api import __version__
from ica_api.api.errors import register_exception_handlers
from ica_api.api.v1.router import api_router
from ica_api.core.config import get_settings
from ica_api.core.logging import configure_logging
from ica_api.infra.db.engine import get_engine


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()

    app = FastAPI(
        title="ICA Durazno API",
        version=__version__,
        description="Sistema de monitoreo fitosanitario del durazno. Uso interno del ICA.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix="/api/v1")

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
