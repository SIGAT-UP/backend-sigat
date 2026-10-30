"""Acceso a datos de concepto y vistas de resumen."""

from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncConnection

from sigat_api.compartido.errores import NoImplementado


class RepositorioConcepto:
    def __init__(self, con: AsyncConnection) -> None:
        self._con = con

    async def resumen(self, lote_id: int) -> dict[str, Any] | None:
        """fn_lote_resumen_app(:usua) WHERE lote_id = :lote."""
        raise NoImplementado("Resumen del lote")

    async def serie(self, lote_id: int, desde: date | None, hasta: date | None) -> list[dict[str, Any]]:
        """fn_mtd_serie_lote(:usua)."""
        raise NoImplementado("Serie del MTD")

    async def periodos(self, lote_id: int) -> list[dict[str, Any]]:
        raise NoImplementado("Periodos")

    async def versiones_mtd(self, peri_id: int) -> list[dict[str, Any]]:
        raise NoImplementado("Versiones del MTD")

    async def conceptos(self, lote_id: int) -> list[dict[str, Any]]:
        raise NoImplementado("Conceptos")

    async def concepto_a_fecha(self, lote_id: int, fecha: date) -> dict[str, Any] | None:
        """Versión vigente con conc_fecha_efecto <= fecha y conc_emitido_en <= fin de ese día."""
        raise NoImplementado("Concepto a fecha")

    async def insertar_concepto(self, fila: dict[str, Any]) -> int:
        """INSERT concepto_aptitud versión n+1 (fn_concepto_valida)."""
        raise NoImplementado("Insertar concepto")

    async def cultivo_productor(self, usua_id: int) -> dict[str, Any]:
        raise NoImplementado("Cultivo del productor")
