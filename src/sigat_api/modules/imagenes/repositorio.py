"""Acceso a datos de archivos y evidencia."""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncConnection

from sigat_api.compartido.errores import NoImplementado


class RepositorioArchivos:
    def __init__(self, con: AsyncConnection) -> None:
        self._con = con

    async def obtener(self, arch_id: UUID) -> dict[str, Any] | None:
        raise NoImplementado("Archivo")

    async def insertar(self, fila: dict[str, Any]) -> None:
        """Estado inicial ``pendiente_contenido`` (fn_archivo_adjunto_valida valida MIME y tamaño)."""
        raise NoImplementado("Alta de archivo")

    async def marcar_almacenado(self, arch_id: UUID, ref: str) -> None:
        raise NoImplementado("Archivo almacenado")

    async def marcar_rechazado(self, arch_id: UUID, motivo: str) -> None:
        raise NoImplementado("Archivo rechazado")

    async def insertar_evidencia(self, fila: dict[str, Any]) -> None:
        raise NoImplementado("Alta de evidencia")
