"""Dependencias HTTP comunes: actor autenticado, permisos y conexión con el actor fijado."""

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncConnection

from sigat_api.compartido.errores import NoAutenticado, Prohibido
from sigat_api.compartido.tipos import Actor
from sigat_api.config import Configuracion, obtener_configuracion
from sigat_api.infra.db.sesion import transaccion
from sigat_api.infra.seguridad.tokens import ServicioTokens
from sigat_api.modules.identidad.permisos import permitido


def configuracion() -> Configuracion:
    return obtener_configuracion()


async def actor_actual(
    request: Request,
    authorization: Annotated[str | None, Header(description="Bearer <token de acceso>")] = None,
    cfg: Configuracion = Depends(configuracion),
) -> Actor:
    """El actor SIEMPRE sale del token (nunca de un id del cuerpo o de la URL)."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise NoAutenticado("Falta el token de acceso.", codigo="TOKEN_AUSENTE")
    reclamos = ServicioTokens(cfg).verificar_acceso(authorization[7:].strip())
    actor = Actor(
        usua_id=reclamos.usua_id,
        rol=reclamos.rol,
        disp_id=reclamos.disp_id,
        cliente=reclamos.cliente,
        emitido_en=reclamos.emitido,
    )
    request.state.actor = actor
    return actor


ActorDep = Annotated[Actor, Depends(actor_actual)]


def requiere(permiso: str) -> Callable[[Actor], Awaitable[Actor]]:
    """Uso: ``actor: Actor = Depends(requiere("planificacion.crear"))``."""

    async def _verificar(actor: ActorDep) -> Actor:
        if not permitido(permiso, actor.rol):
            raise Prohibido(f"Su rol no permite: {permiso}.", codigo="ROL_SIN_PERMISO")
        return actor

    return _verificar


async def conexion(actor: ActorDep) -> AsyncIterator[AsyncConnection]:
    """Una transacción por petición con ``sigat.usuario_actual`` = actor (SET LOCAL)."""
    async with transaccion(actor) as con:
        yield con


async def conexion_publica() -> AsyncIterator[AsyncConnection]:
    """Solo para login, refresco y recuperación (no hay actor todavía)."""
    async with transaccion(None) as con:
        yield con


ConexionDep = Annotated[AsyncConnection, Depends(conexion)]
ConexionPublicaDep = Annotated[AsyncConnection, Depends(conexion_publica)]
