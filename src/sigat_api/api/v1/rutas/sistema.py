"""Rutas de sistema: salud, hora del servidor y versión. Públicas."""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Request

from sigat_api import __version__
from sigat_api.api.v1 import esquemas_compuestos as c
from sigat_api.compartido.errores import NoImplementado
from sigat_api.config import obtener_configuracion

router = APIRouter(tags=["Sistema"])


@router.get("/salud", response_model=c.Salud, summary="Vida del proceso (sin tocar dependencias)")
async def salud() -> c.Salud:
    return c.Salud(estado="ok")


@router.get("/salud/listo", response_model=c.Listo, summary="Listo para atender (BD, almacén, cola)")
async def listo() -> c.Listo:
    raise NoImplementado("Comprobación de dependencias")


@router.get(
    "/sistema/hora", response_model=c.HoraServidor, summary="Hora del servidor (deriva de reloj, R-T6)"
)
async def hora() -> c.HoraServidor:
    cfg = obtener_configuracion()
    return c.HoraServidor(
        servidor_utc=datetime.now(UTC), zona_horaria_predeterminada=cfg.zona_horaria_predeterminada
    )


@router.get("/sistema/version", response_model=c.VersionServicio, summary="Versión de la API y del contrato")
async def version(request: Request) -> c.VersionServicio:
    cfg = obtener_configuracion()
    return c.VersionServicio(
        api=__version__,
        contrato=_huella_contrato(request.app.openapi()),
        version_minima_app=cfg.version_minima_app,
    )


_huellas: dict[int, str] = {}


def _huella_contrato(contrato: dict[str, Any]) -> str:
    """Hash corto del contrato publicado (12 caracteres de su SHA-256)."""
    clave = id(contrato)
    if clave not in _huellas:
        datos = json.dumps(contrato, sort_keys=True, ensure_ascii=False).encode("utf-8")
        _huellas[clave] = hashlib.sha256(datos).hexdigest()[:12]
    return _huellas[clave]
