"""Rutas HTTP del módulo imagenes. El router solo traduce HTTP a casos de uso."""

from fastapi import APIRouter

router = APIRouter(prefix="/imagenes", tags=["imagenes"])
