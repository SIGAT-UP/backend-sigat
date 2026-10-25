"""Rutas HTTP del módulo identidad. El router solo traduce HTTP a casos de uso."""

from fastapi import APIRouter

router = APIRouter(prefix="/identidad", tags=["identidad"])
