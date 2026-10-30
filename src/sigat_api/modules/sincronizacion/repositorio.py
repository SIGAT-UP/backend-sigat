"""Acceso a datos de sincronización."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from sigat_api.compartido.errores import NoImplementado


class RepositorioSincronizacion:
    def __init__(self, con: AsyncConnection) -> None:
        self._con = con

    async def dispositivo(self, disp_id: UUID) -> dict[str, Any] | None:
        fila = (
            (
                await self._con.execute(
                    text(
                        "SELECT disp_id, disp_nombre, disp_plataforma, disp_version_app, disp_activo"
                        " FROM sigat.dispositivo WHERE disp_id = :d"
                    ),
                    {"d": disp_id},
                )
            )
            .mappings()
            .first()
        )
        return dict(fila) if fila else None

    async def upsert_dispositivo(
        self, disp_id: UUID | None, plataforma: str, version_app: str | None, nombre: str | None
    ) -> UUID:
        """Crea el dispositivo o actualiza versión y nombre del existente (activo)."""
        if disp_id is not None:
            await self._con.execute(
                text(
                    "UPDATE sigat.dispositivo SET disp_version_app = coalesce(:v, disp_version_app),"
                    " disp_nombre = coalesce(:n, disp_nombre) WHERE disp_id = :d"
                ),
                {"v": version_app, "n": nombre, "d": disp_id},
            )
            return disp_id
        nuevo = await self._con.scalar(
            text(
                "INSERT INTO sigat.dispositivo (disp_plataforma, disp_version_app, disp_nombre)"
                " VALUES (:p, :v, :n) RETURNING disp_id"
            ),
            {"p": plataforma, "v": version_app, "n": nombre},
        )
        return UUID(str(nuevo))

    async def operacion_existente(self, disp_id: UUID, cliente_id: UUID) -> dict[str, Any] | None:
        """Busca por la clave única (disp_id, oper_cliente_id)."""
        raise NoImplementado("Operación existente")

    async def registrar_reenvio(self, oper_id: int, hash_hex: str, resultado: str) -> None:
        """INSERT recepcion_sync (idempotente_repetida | conflicto_contenido)."""
        raise NoImplementado("Registrar reenvío")

    async def insertar_operacion(self, fila: dict[str, Any]) -> int:
        """INSERT operacion_sync. ``oper_payload`` SOLO si la clasificación es revisar/rechazada."""
        raise NoImplementado("Insertar operación")

    async def fijar_clasificacion(
        self, oper_id: int, clasificacion: str, motivo: str | None, payload: dict[str, Any] | None
    ) -> None:
        """Se inserta la operación con la clasificación ya decidida (tabla append-only):
        el orden real es decidir -> insertar operación -> insertar dominio en la misma transacción."""
        raise NoImplementado("Clasificación")

    async def pendientes_de_usuario(self, usua_id: int, clasificaciones: list[str]) -> list[dict[str, Any]]:
        """Operaciones revisar/rechazada sin otra que las resuelva (oper_resuelve_oper_id)."""
        raise NoImplementado("Pendientes")

    async def cambios_desde(
        self, usua_id: int, disp_id: UUID, desde: datetime | None, limite: int
    ) -> list[dict[str, Any]]:
        raise NoImplementado("Cambios desde cursor")
