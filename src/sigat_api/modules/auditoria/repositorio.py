"""Consulta de bitácora."""

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncConnection

from sigat_api.compartido.errores import NoImplementado


class RepositorioAuditoria:
    def __init__(self, con: AsyncConnection) -> None:
        self._con = con

    async def listar(
        self,
        desde: datetime | None,
        hasta: datetime | None,
        tablas: list[str] | None,
        usua_id: int | None,
        cursor: str | None,
    ) -> Any:
        raise NoImplementado("Bitácora")

    async def registrar_acceso(
        self, usua_id: int, tabla: str, registro: str, detalle: dict[str, Any]
    ) -> None:
        raise NoImplementado("Registrar acceso")
