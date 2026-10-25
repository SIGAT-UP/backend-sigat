"""Rutas HTTP del módulo reportes. El router solo traduce HTTP a casos de uso."""

from fastapi import APIRouter

router = APIRouter(prefix="/reportes", tags=["reportes"])
