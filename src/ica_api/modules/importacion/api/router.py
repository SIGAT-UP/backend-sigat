"""Rutas HTTP del módulo importacion. El router solo traduce HTTP a casos de uso."""

from fastapi import APIRouter

router = APIRouter(prefix="/importacion", tags=["importacion"])
