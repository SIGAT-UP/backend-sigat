"""Middleware: traza por petición, control de versión mínima de la app y cabeceras de seguridad."""

import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from sigat_api.config import Configuracion


def registrar_middleware(app: FastAPI, cfg: Configuracion) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origenes,  # solo los orígenes de la web; el móvil no usa CORS
        allow_credentials=True,  # necesario para la cookie del refresco
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "If-None-Match",
            "If-Match",
            "X-App-Version",
            "X-Traza-Id",
        ],
        expose_headers=["ETag", "X-Traza-Id"],
    )

    @app.middleware("http")
    async def traza(request: Request, siguiente: Callable[[Request], Awaitable[Response]]) -> Response:
        traza_id = request.headers.get("X-Traza-Id") or str(uuid.uuid4())
        request.state.traza_id = traza_id
        structlog.contextvars.bind_contextvars(traza_id=traza_id, ruta=request.url.path)
        try:
            respuesta = await siguiente(request)
        finally:
            structlog.contextvars.clear_contextvars()
        respuesta.headers["X-Traza-Id"] = traza_id
        respuesta.headers["X-Content-Type-Options"] = "nosniff"
        respuesta.headers["Referrer-Policy"] = "no-referrer"
        respuesta.headers["Cache-Control"] = respuesta.headers.get("Cache-Control", "no-store")
        return respuesta

    # Pendiente: si SIGAT_VERSION_MINIMA_APP está definida y la cabecera X-App-Version del móvil es
    # menor, responder 426 con código APP_DESACTUALIZADA (la app instalada en campo debe saberlo).
