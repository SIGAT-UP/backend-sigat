"""Rutas HTTP del módulo laboratorio. El router solo traduce HTTP a casos de uso."""

from fastapi import APIRouter

router = APIRouter(prefix="/laboratorio", tags=["laboratorio"])
