"""Acceso a datos de catálogos (SQL dinámico SOLO sobre tablas de ``dominio.CATALOGOS``)."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from sigat_api.compartido.errores import NoImplementado
from sigat_api.modules.catalogo.dominio import DefinicionCatalogo


class RepositorioCatalogo:
    def __init__(self, con: AsyncConnection) -> None:
        self._con = con

    async def columnas(self, cat: DefinicionCatalogo) -> list[str]:
        filas = await self._con.execute(
            text(
                "SELECT column_name FROM information_schema.columns"
                " WHERE table_schema = 'sigat' AND table_name = :t ORDER BY ordinal_position"
            ),
            {"t": cat.tabla},
        )
        return [str(f[0]) for f in filas]

    async def items(self, cat: DefinicionCatalogo, incluir_inactivos: bool) -> list[dict[str, Any]]:
        """Nunca interpolar el nombre de tabla desde la petición: solo desde ``DefinicionCatalogo``."""
        filtro = ""
        if cat.columna_activo and not incluir_inactivos:
            filtro = f" WHERE {cat.columna_activo}"
        filas = await self._con.execute(
            text(f"SELECT * FROM sigat.{cat.tabla}{filtro} ORDER BY {cat.prefijo}_id")  # noqa: S608
        )
        return [dict(f) for f in filas.mappings()]

    async def total(self, cat: DefinicionCatalogo) -> int:
        return int(await self._con.scalar(text(f"SELECT count(*) FROM sigat.{cat.tabla}")) or 0)  # noqa: S608

    async def en_uso(self, cat: DefinicionCatalogo, item_id: int) -> bool:
        raise NoImplementado("Comprobación de uso")

    async def guardar(self, cat: DefinicionCatalogo, items: list[dict[str, Any]]) -> None:
        raise NoImplementado("Guardar catálogo")

    async def departamentos(self) -> list[dict[str, Any]]:
        filas = await self._con.execute(
            text(
                "SELECT depa_id, depa_codigo, depa_descripcion FROM sigat.departamento ORDER BY depa_descripcion"
            )
        )
        return [dict(f) for f in filas.mappings()]

    async def municipios(self, depa_id: int | None) -> list[dict[str, Any]]:
        filas = await self._con.execute(
            text(
                """
SELECT m.muni_id, m.muni_codigo, m.muni_descripcion, m.depa_id, d.depa_codigo || m.muni_codigo AS divipola
  FROM sigat.municipio m JOIN sigat.departamento d ON d.depa_id = m.depa_id
 WHERE CAST(:d AS integer) IS NULL OR m.depa_id = CAST(:d AS integer)
 ORDER BY m.muni_descripcion"""
            ),
            {"d": depa_id},
        )
        return [dict(f) for f in filas.mappings()]
