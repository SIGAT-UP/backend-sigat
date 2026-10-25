"""Rutas HTTP del módulo sincronizacion. El router solo traduce HTTP a casos de uso."""

from fastapi import APIRouter

router = APIRouter(prefix="/sincronizacion", tags=["sincronizacion"])
