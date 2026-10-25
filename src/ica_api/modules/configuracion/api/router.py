"""Rutas HTTP del módulo configuracion. El router solo traduce HTTP a casos de uso."""

from fastapi import APIRouter

router = APIRouter(prefix="/configuracion", tags=["configuracion"])
