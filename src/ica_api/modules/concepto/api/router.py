"""Rutas HTTP del módulo concepto. El router solo traduce HTTP a casos de uso."""

from fastapi import APIRouter

router = APIRouter(prefix="/concepto", tags=["concepto"])
