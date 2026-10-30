"""Traducción de errores a ``application/problem+json`` (RFC 9457).

Todos los errores, sin excepción, salen con esta forma. Los fronts leen
``codigo`` (estable) para decidir y ``detail`` (español, para personas) para mostrar.
"""

import uuid
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError
from starlette.exceptions import HTTPException as StarletteHTTPException

from sigat_api.compartido.errores import ErrorDominio
from sigat_api.infra.db.errores_pg import traducir

TIPO_BASE = "https://sigat-durazno/errores/"
MEDIA = "application/problem+json"
log = structlog.get_logger()


def _mensaje_validacion(e: Any) -> str:
    """Mensaje en español para los errores más comunes de pydantic; los propios ya vienen en español."""
    ctx = e.get("ctx") or {}
    tipo = e.get("type", "")
    mensajes = {
        "missing": "Es obligatorio.",
        "string_too_short": f"Debe tener al menos {ctx.get('min_length')} caracteres.",
        "too_short": f"Debe tener al menos {ctx.get('min_length')} caracteres.",
        "string_too_long": f"Debe tener como máximo {ctx.get('max_length')} caracteres.",
        "too_long": f"Debe tener como máximo {ctx.get('max_length')} caracteres.",
        "int_parsing": "Debe ser un número entero.",
        "float_parsing": "Debe ser un número.",
        "bool_parsing": "Debe ser verdadero o falso.",
        "greater_than": f"Debe ser mayor que {ctx.get('gt')}.",
        "greater_than_equal": f"Debe ser mayor o igual que {ctx.get('ge')}.",
        "less_than_equal": f"Debe ser menor o igual que {ctx.get('le')}.",
        "enum": f"Valor no permitido. Opciones: {ctx.get('expected')}.",
        "literal_error": f"Valor no permitido. Opciones: {ctx.get('expected')}.",
        "string_pattern_mismatch": "El formato no es válido.",
        "date_from_datetime_parsing": "Fecha no válida (AAAA-MM-DD).",
        "datetime_from_date_parsing": "Fecha y hora no válidas (ISO 8601).",
        "extra_forbidden": "Campo no permitido.",
        "json_invalid": "El cuerpo no es JSON válido.",
    }
    mensaje = str(e.get("msg", "")).removeprefix("Value error, ")
    if "email address" in mensaje:  # email-validator responde en inglés
        return "El correo no es válido."
    return mensajes.get(tipo) or mensaje


def _problema(
    request: Request,
    estado: int,
    titulo: str,
    detalle: str,
    codigo: str,
    errores: list[dict[str, str]] | None = None,
) -> JSONResponse:
    traza = getattr(request.state, "traza_id", None) or str(uuid.uuid4())
    cuerpo = {
        "type": TIPO_BASE + codigo.lower(),
        "title": titulo,
        "status": estado,
        "detail": detalle,
        "instance": request.url.path,
        "codigo": codigo,
        "errores": errores or [],
        "traza_id": traza,
    }
    return JSONResponse(cuerpo, status_code=estado, media_type=MEDIA)


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(ErrorDominio)
    async def _dominio(request: Request, exc: ErrorDominio) -> JSONResponse:
        return _problema(request, exc.estado_http, exc.titulo, exc.detalle, exc.codigo, exc.errores)

    @app.exception_handler(RequestValidationError)
    async def _validacion(request: Request, exc: RequestValidationError) -> JSONResponse:
        errores = [
            {
                "campo": ".".join(str(p) for p in e["loc"] if p != "body"),
                "mensaje": _mensaje_validacion(e),
            }
            for e in exc.errors()
        ]
        # El primer mensaje va también en ``detail``: es lo que muestran las pantallas.
        primero = errores[0] if errores else None
        detalle = (
            f"{primero['campo']}: {primero['mensaje']}"
            if primero and primero["campo"]
            else (primero or {}).get("mensaje")
        ) or "Revise los campos marcados."
        return _problema(request, 422, "Datos con forma no válida", detalle, "VALIDACION", errores)

    @app.exception_handler(DBAPIError)
    async def _bd(request: Request, exc: DBAPIError) -> JSONResponse:
        log.warning("bd_rechazo", error=str(exc.orig) if exc.orig else str(exc))
        err = traducir(exc)
        return _problema(request, err.estado_http, err.titulo, err.detalle, err.codigo)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        codigo = {404: "RUTA_NO_ENCONTRADA", 405: "METODO_NO_PERMITIDO"}.get(exc.status_code, "HTTP")
        return _problema(request, exc.status_code, "Solicitud no válida", str(exc.detail), codigo)

    @app.exception_handler(Exception)
    async def _inesperado(request: Request, exc: Exception) -> JSONResponse:
        log.exception("error_inesperado")
        return _problema(
            request, 500, "Error interno", "Ocurrió un error inesperado. Intente de nuevo.", "ERROR_INTERNO"
        )
