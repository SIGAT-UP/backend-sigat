"""Rutas HTTP del módulo calidad. El router solo traduce HTTP a casos de uso."""

from fastapi import APIRouter

router = APIRouter(prefix="/calidad", tags=["calidad"])
