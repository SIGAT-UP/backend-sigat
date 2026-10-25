"""Formato único de error de la API.

Toda respuesta de error tiene la misma forma, para que el móvil y la web
muestren el mensaje sin adivinar el esquema:

    {"codigo": "PREDIO_NO_ENCONTRADO", "mensaje": "...", "detalle": {...}}
"""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class APIError(Exception):
    """Error de negocio con un código estable."""

    def __init__(
        self,
        codigo: str,
        mensaje: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        detalle: dict[str, Any] | None = None,
    ) -> None:
        self.codigo = codigo
        self.mensaje = mensaje
        self.status_code = status_code
        self.detalle = detalle or {}
        super().__init__(mensaje)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def handle_api_error(_: Request, exc: APIError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"codigo": exc.codigo, "mensaje": exc.mensaje, "detalle": exc.detalle},
        )
