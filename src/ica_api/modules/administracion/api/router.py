"""Rutas HTTP del módulo administracion. El router solo traduce HTTP a casos de uso."""

from fastapi import APIRouter

router = APIRouter(prefix="/administracion", tags=["administracion"])
