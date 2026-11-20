"""Casos de uso de notificaciones."""

import base64
import binascii
import json
from datetime import UTC, datetime
from typing import cast

from sigat_api.compartido.errores import NoEncontrado, NoImplementado
from sigat_api.compartido.esquemas import Pagina
from sigat_api.compartido.tipos import Actor, CategoriaNotificacion
from sigat_api.modules.notificaciones import esquemas as e
from sigat_api.modules.notificaciones.repositorio import RepositorioNotificaciones

TAMANO_PAGINA = 50


def _a_notificacion(f: dict[str, object]) -> e.Notificacion:
    ruta = f.get("noti_destino_ruta")
    return e.Notificacion(
        noti_id=int(str(f["noti_id"])),
        categoria=CategoriaNotificacion(str(f["cate_codigo"])),
        titulo=str(f["noti_titulo"]),
        cuerpo=str(f["noti_cuerpo"]),
        creada_en=f["noti_creada_en"],
        leida_en=f["noti_leida_en"],
        leida=f["noti_leida_en"] is not None,
        destino=e.DestinoNotificacion(
            ruta=str(ruta),
            argumento=str(f["noti_destino_argumento"]) if f.get("noti_destino_argumento") else None,
        )
        if ruta
        else None,
    )


def _codificar(fila: dict[str, object]) -> str:
    creada = cast(datetime, fila["noti_creada_en"])
    clave = json.dumps([creada.isoformat(), int(str(fila["noti_id"]))])
    return base64.urlsafe_b64encode(clave.encode()).decode().rstrip("=")


def _decodificar(cursor: str | None) -> tuple[datetime, int] | None:
    """Un cursor ilegible se trata como «primera página», igual que antes del cambio de orden."""
    if not cursor:
        return None
    try:
        creada, noti_id = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
        return datetime.fromisoformat(creada), int(noti_id)
    except (binascii.Error, ValueError, TypeError):
        return None


class ServicioNotificaciones:
    """Implementa además ``identidad.puertos.PuertoAvisos`` (método ``emitir``)."""

    def __init__(self, repo: RepositorioNotificaciones) -> None:
        self._repo = repo

    async def listar(self, actor: Actor, cursor: str | None) -> Pagina[e.Notificacion]:
        """Bandeja del actor: solo no leídas, más reciente primero (decisión del Owner, Sprint 3).
        ``cursor`` = el ``siguiente`` de la página anterior."""
        filas = await self._repo.listar(actor.usua_id, _decodificar(cursor), TAMANO_PAGINA + 1)
        items = [_a_notificacion(f) for f in filas[:TAMANO_PAGINA]]
        ultima = filas[TAMANO_PAGINA - 1] if len(filas) > TAMANO_PAGINA else None
        siguiente = _codificar(ultima) if ultima else None
        return Pagina[e.Notificacion](items=items, siguiente=siguiente)

    async def conteo(self, actor: Actor) -> e.ConteoNoLeidas:
        return e.ConteoNoLeidas(no_leidas=await self._repo.conteo_no_leidas(actor.usua_id))

    async def marcar_leida(self, actor: Actor, noti_id: int) -> None:
        """De otro usuario -> 404 (no revelar que existe)."""
        if not await self._repo.marcar_leida(actor.usua_id, noti_id, datetime.now(UTC)):
            raise NoEncontrado("El aviso no existe.", codigo="AVISO_NO_ENCONTRADO")

    async def marcar_todas(self, actor: Actor) -> None:
        await self._repo.marcar_todas(actor.usua_id, datetime.now(UTC))

    async def preferencias(self, actor: Actor) -> e.PreferenciasNotificacion:
        raise NoImplementado("Preferencias de notificación")

    async def guardar_preferencias(
        self, actor: Actor, s: e.PreferenciasNotificacion
    ) -> e.PreferenciasNotificacion:
        raise NoImplementado("Guardar preferencias de notificación")

    async def emitir(
        self,
        usua_id: int,
        categoria: str,
        titulo: str,
        cuerpo: str,
        evento_clave: str,
        ruta: str | None = None,
        argumento: str | None = None,
    ) -> bool:
        """Para eventos del backend (no de la BD). Idempotente por evento_clave. True si lo creó."""
        return await self._repo.crear(usua_id, categoria, titulo, cuerpo, evento_clave, ruta, argumento)
