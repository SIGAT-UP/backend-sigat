"""Acceso a datos de notificaciones. Siempre filtrado por el usuario dueño del aviso."""

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from sigat_api.compartido.errores import NoImplementado

_COLUMNAS = """
SELECT n.noti_id, c.cate_codigo, n.noti_titulo, n.noti_cuerpo, n.noti_creada_en, n.noti_leida_en,
       n.noti_destino_ruta, n.noti_destino_argumento
  FROM sigat.notificacion n
  JOIN sigat.categoria_notificacion c ON c.cate_id = n.cate_id
"""


class RepositorioNotificaciones:
    def __init__(self, con: AsyncConnection) -> None:
        self._con = con

    async def listar(
        self, usua_id: int, solo_no_leidas: bool, antes_de: int | None, limite: int
    ) -> list[dict[str, Any]]:
        """Más reciente primero; paginación por ``noti_id`` (``antes_de`` = último id recibido)."""
        filas = await self._con.execute(
            text(
                _COLUMNAS
                + """
 WHERE n.usua_id = :u
   AND (NOT :solo OR n.noti_leida_en IS NULL)
   AND (CAST(:antes AS bigint) IS NULL OR n.noti_id < CAST(:antes AS bigint))
 ORDER BY n.noti_id DESC
 LIMIT :lim"""
            ),
            {"u": usua_id, "solo": solo_no_leidas, "antes": antes_de, "lim": limite},
        )
        return [dict(f) for f in filas.mappings()]

    async def conteo_no_leidas(self, usua_id: int) -> int:
        valor = await self._con.scalar(
            text("SELECT count(*) FROM sigat.notificacion WHERE usua_id = :u AND noti_leida_en IS NULL"),
            {"u": usua_id},
        )
        return int(valor or 0)

    async def marcar_leida(self, usua_id: int, noti_id: int, momento: datetime) -> bool:
        """Devuelve False si el aviso no existe o es de otro usuario. Leer dos veces no es error."""
        existe = await self._con.scalar(
            text("SELECT noti_leida_en IS NULL FROM sigat.notificacion WHERE noti_id = :n AND usua_id = :u"),
            {"n": noti_id, "u": usua_id},
        )
        if existe is None:
            return False
        if existe:
            await self._con.execute(
                text("UPDATE sigat.notificacion SET noti_leida_en = :t WHERE noti_id = :n AND usua_id = :u"),
                {"t": momento, "n": noti_id, "u": usua_id},
            )
        return True

    async def marcar_todas(self, usua_id: int, momento: datetime) -> int:
        resultado = await self._con.execute(
            text(
                "UPDATE sigat.notificacion SET noti_leida_en = :t WHERE usua_id = :u AND noti_leida_en IS NULL"
            ),
            {"t": momento, "u": usua_id},
        )
        return int(resultado.rowcount or 0)

    async def crear(
        self,
        usua_id: int,
        categoria: str,
        titulo: str,
        cuerpo: str,
        evento_clave: str,
        ruta: str | None,
        argumento: str | None,
    ) -> bool:
        """Idempotente por (usua_id, noti_evento_clave). No crea el aviso si la persona apagó
        esa categoría en sus preferencias. Devuelve True si lo creó."""
        creada = await self._con.scalar(
            text(
                """
INSERT INTO sigat.notificacion
       (usua_id, cate_id, noti_titulo, noti_cuerpo, noti_evento_clave, noti_destino_ruta, noti_destino_argumento)
SELECT :u, c.cate_id, :t, :c, :k, :r, :a
  FROM sigat.categoria_notificacion c
 WHERE c.cate_codigo = :cat
   AND NOT EXISTS (SELECT 1 FROM sigat.preferencia_notificacion p
                    WHERE p.usua_id = :u AND p.cate_id = c.cate_id AND NOT p.pref_habilitada)
ON CONFLICT (usua_id, noti_evento_clave) DO NOTHING
RETURNING noti_id"""
            ),
            {
                "u": usua_id,
                "t": titulo,
                "c": cuerpo,
                "k": evento_clave,
                "r": ruta,
                "a": argumento,
                "cat": categoria,
            },
        )
        return creada is not None

    async def preferencias(self, usua_id: int) -> dict[str, Any]:
        raise NoImplementado("Preferencias de notificación")

    async def guardar_preferencias(self, usua_id: int, activas: bool, categorias: dict[str, bool]) -> None:
        raise NoImplementado("Guardar preferencias de notificación")
