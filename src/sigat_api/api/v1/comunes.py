"""Piezas comunes de las rutas v1."""

from typing import Annotated, Any

from fastapi import Query

from sigat_api.compartido.esquemas import Problema

_P: dict[str, Any] = {"model": Problema, "content": {"application/problem+json": {}}}

ERRORES: dict[int | str, dict[str, Any]] = {401: _P, 403: _P, 404: _P, 409: _P, 422: _P, 501: _P}
ERRORES_PUBLICOS: dict[int | str, dict[str, Any]] = {401: _P, 422: _P, 429: _P, 501: _P}

Cursor = Annotated[str | None, Query(description="Cursor opaco devuelto en 'siguiente'.")]
Limite = Annotated[int, Query(ge=1, le=200, description="Máximo de elementos por página.")]
