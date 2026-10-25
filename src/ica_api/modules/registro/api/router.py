"""Rutas HTTP del módulo registro. El router solo traduce HTTP a casos de uso."""

from fastapi import APIRouter

router = APIRouter(prefix="/registro", tags=["registro"])
