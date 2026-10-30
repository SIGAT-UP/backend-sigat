"""Enrutador raíz de la versión 1 (``/api/v1``)."""

from fastapi import APIRouter

from sigat_api.api.v1.rutas import (
    administracion,
    archivos,
    auth,
    catalogos,
    lotes,
    planificaciones,
    predios,
    productor,
    registro,
    sincronizacion,
    sistema,
    trampas,
    yo,
)

router_v1 = APIRouter()
for modulo in (
    sistema,
    auth,
    yo,
    administracion,
    catalogos,
    predios,
    lotes,
    trampas,
    registro,
    sincronizacion,
    archivos,
    planificaciones,
    productor,
):
    router_v1.include_router(modulo.router)
