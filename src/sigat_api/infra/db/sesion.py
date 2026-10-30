"""Unidad de trabajo por petición con el ACTOR fijado en la BD.

Requisito duro de SIGAT v8: los disparadores leen ``sigat.fn_usuario_actual()``,
que devuelve ``current_setting('sigat.usuario_actual')``. Por eso CADA
transacción que escribe (y las de lectura que dependen de ``fn_lotes_visibles``)
debe ejecutar primero::

    SELECT set_config('sigat.usuario_actual', :usua_id, true)   -- true = SET LOCAL

``SET LOCAL`` muere con la transacción, así que una conexión del pool nunca
arrastra el actor de otra petición. El valor sale del TOKEN, jamás del cuerpo.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from sigat_api.compartido.errores import NoAutenticado
from sigat_api.compartido.tipos import Actor
from sigat_api.infra.db.motor import obtener_motor

# Fija el actor y, en la misma consulta, comprueba que el token siga vigente: el token de acceso es
# un JWT sin estado, así que sin esto una cuenta desactivada, eliminada, con otro rol o a la que el
# administrador le asignó contraseña conservaría el acceso hasta que el token venza (15 min).
# Una sesión revocada DESPUÉS de emitido el token (en ese dispositivo, o en todos) lo invalida.
# ``iat`` viene en segundos enteros: se le suma 1 s para no invalidar un login hecho en el mismo
# segundo que la revocación.
_FIJAR_ACTOR = text(
    """
SELECT set_config('sigat.usuario_actual', CAST(:u AS text), true) IS NOT NULL
   AND (CAST(:emitido AS timestamptz) IS NULL OR EXISTS (
        SELECT 1 FROM sigat.usuario us
          JOIN sigat.rol r ON r.rol_id = us.rol_id
          JOIN sigat.estado_registro e ON e.esta_id = us.esta_id
         WHERE us.usua_id = CAST(:u AS integer) AND us.usua_eliminado_en IS NULL
           AND e.esta_descripcion = 'activo' AND r.rol_codigo = :rol
           AND NOT EXISTS (
               SELECT 1 FROM api.sesion_refresco s
                WHERE s.usua_id = us.usua_id
                  AND s.sesr_revocado_en >= CAST(:emitido AS timestamptz) + interval '1 second'
                  AND (CAST(:disp AS uuid) IS NULL OR s.disp_id = CAST(:disp AS uuid)))))"""
)


def _parametros(actor: Actor) -> dict[str, object]:
    return {
        "u": str(actor.usua_id),
        "rol": actor.rol.value,
        "emitido": actor.emitido_en,
        "disp": str(actor.disp_id) if actor.disp_id else None,
    }


@asynccontextmanager
async def transaccion(actor: Actor | None) -> AsyncIterator[AsyncConnection]:
    """Abre una transacción; confirma al salir sin error y revierte si hay excepción.

    ``actor=None`` solo para rutas públicas (login, recuperación, salud).
    """
    async with obtener_motor().begin() as con:
        if actor is not None:
            vigente = await con.scalar(_FIJAR_ACTOR, _parametros(actor))
            if not vigente:
                raise NoAutenticado(
                    "Su sesión ya no es válida (la cuenta cambió o se cerró). Inicie sesión de nuevo.",
                    codigo="SESION_REVOCADA",
                )
        yield con


@asynccontextmanager
async def solo_lectura(actor: Actor | None) -> AsyncIterator[AsyncConnection]:
    """Transacción de solo lectura (``SET TRANSACTION READ ONLY``) con el actor fijado."""
    async with transaccion(actor) as con:
        await con.execute(text("SET TRANSACTION READ ONLY"))
        yield con
