"""Comandos de administración por consola (no existen como rutas HTTP).

Uso (entorno virtual activo y ``.env`` configurado con ``SIGAT_DB_URL``)::

    python -m sigat_api.cli inicializar-admin --cedula 1000000000 --nombre Usuario --apellido Prueba \\
        --usuario usuario.prueba --correo usuario@ejemplo.test \\
        --centro "Centro de acopio de ejemplo" --departamento-codigo 00 --departamento "Departamento de ejemplo"
    python -m sigat_api.cli referencias
    python -m sigat_api.cli registrar-municipio --departamento-codigo 00 --codigo 000 --nombre "Municipio de ejemplo"
    python -m sigat_api.cli hash-contrasena

``inicializar-admin`` crea el PRIMER administrador de una base sin administradores. Es la única
forma de crear una cuenta fuera de la aplicación y está protegida así:

* Solo funciona si la base NO tiene ningún administrador activo (se comprueba dentro de la misma
  transacción, con un bloqueo, para que dos ejecuciones simultáneas no creen dos).
* Requiere acceso directo a la base (``SIGAT_DB_URL``): quien no administra el entorno no puede usarlo.
* En ``SIGAT_ENTORNO=produccion`` exige además ``--entorno-produccion``.
* La contraseña se pide por teclado (o por la entrada estándar con ``--contrasena-stdin``), nunca
  como argumento, y se guarda solo como hash argon2id.

Los demás usuarios los crea ese administrador desde la web (Administración → Usuarios).
"""

import argparse
import asyncio
import getpass
import sys
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from sigat_api.compartido.tipos import RolCodigo
from sigat_api.config import obtener_configuracion
from sigat_api.infra.db.motor import cerrar_motor, crear_motor
from sigat_api.infra.db.sesion import transaccion
from sigat_api.infra.seguridad import contrasenas
from sigat_api.modules.identidad.repositorio import RepositorioIdentidad

LONGITUD_MINIMA = 10
# Clave del bloqueo consultivo que serializa la creación del primer administrador.
_BLOQUEO_PRIMER_ADMIN = 7_402_026


class ErrorComando(Exception):
    """Error esperado: se muestra el mensaje y el comando termina con código 2."""


def _pedir_contrasena(desde_stdin: bool) -> str:
    if desde_stdin:
        clave = sys.stdin.readline().rstrip("\n")
        if len(clave) < LONGITUD_MINIMA:
            raise ErrorComando("La contraseña debe tener al menos 10 caracteres.")
        return clave
    while True:
        primera = getpass.getpass("Contraseña (mínimo 10 caracteres): ")
        if len(primera) < LONGITUD_MINIMA:
            print("Muy corta. Intente de nuevo.")
            continue
        if getpass.getpass("Repita la contraseña: ") != primera:
            print("No coinciden. Intente de nuevo.")
            continue
        return primera


async def _id_departamento(con: AsyncConnection, codigo: str, nombre: str | None, region: str | None) -> int:
    depa = await con.scalar(
        text("SELECT depa_id FROM sigat.departamento WHERE depa_codigo = :c"), {"c": codigo}
    )
    if depa is not None:
        return int(depa)
    if not nombre:
        raise ErrorComando(
            f'El departamento {codigo} no está registrado. Agregue --departamento "Nombre" (y --region) para crearlo.'
        )
    regi = await con.scalar(
        text("SELECT regi_id FROM sigat.region WHERE regi_descripcion = :r"), {"r": region or "Sin región"}
    )
    if regi is None:
        regi = await con.scalar(
            text("INSERT INTO sigat.region (regi_descripcion) VALUES (:r) RETURNING regi_id"),
            {"r": region or "Sin región"},
        )
    return int(
        await con.scalar(
            text(
                "INSERT INTO sigat.departamento (depa_descripcion, regi_id, depa_codigo)"
                " VALUES (:n, :r, :c) RETURNING depa_id"
            ),
            {"n": nombre, "r": regi, "c": codigo},
        )
    )


async def _id_centro(con: AsyncConnection, a: argparse.Namespace) -> int:
    if a.centro_id is not None:
        existe = await con.scalar(
            text("SELECT cent_id FROM sigat.centro_acopio WHERE cent_id = :i"), {"i": a.centro_id}
        )
        if existe is None:
            raise ErrorComando(
                f"No existe el centro de acopio {a.centro_id} (vea: python -m sigat_api.cli referencias)."
            )
        return int(existe)
    if not a.centro:
        raise ErrorComando(
            'Indique --centro-id (uno existente) o --centro "Nombre" con --departamento-codigo.'
        )
    existente = await con.scalar(
        text("SELECT cent_id FROM sigat.centro_acopio WHERE lower(cent_descripcion) = lower(:n)"),
        {"n": a.centro},
    )
    if existente is not None:
        return int(existente)
    if not a.departamento_codigo:
        raise ErrorComando("Para crear el centro de acopio indique --departamento-codigo (2 dígitos DANE).")
    depa = await _id_departamento(con, a.departamento_codigo, a.departamento, a.region)
    return int(
        await con.scalar(
            text(
                "INSERT INTO sigat.centro_acopio (cent_descripcion, depa_id) VALUES (:n, :d) RETURNING cent_id"
            ),
            {"n": a.centro, "d": depa},
        )
    )


async def inicializar_admin(a: argparse.Namespace, contrasena: str) -> int:
    """Crea el primer administrador. Lanza ``ErrorComando`` si ya hay uno activo. Devuelve usua_id."""
    cfg = obtener_configuracion()
    if cfg.entorno == "produccion" and not a.entorno_produccion:
        raise ErrorComando(
            "SIGAT_ENTORNO=produccion: confirme que es intencional agregando --entorno-produccion."
        )
    if contrasena.strip().lower() in {a.usuario.strip().lower(), (a.correo or "").strip().lower()}:
        raise ErrorComando("La contraseña no puede ser igual al usuario ni al correo.")
    async with transaccion(None) as con:
        await con.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _BLOQUEO_PRIMER_ADMIN})
        repo = RepositorioIdentidad(con)
        if await repo.administradores_activos():
            raise ErrorComando(
                "La base ya tiene un administrador activo. Este comando solo inicializa una base vacía: "
                "pida a un administrador que cree su usuario desde la web."
            )
        cent_id = await _id_centro(con, a)
        datos: dict[str, Any] = {
            "pers_cc": a.cedula,
            "nombre": a.nombre.strip(),
            "apellido": a.apellido.strip(),
            "correo": a.correo,
            "telefono": a.telefono,
            "direccion": None,
            "usuario": a.usuario.strip(),
            "hash_contrasena": contrasenas.generar_hash(contrasena),
            "rol": RolCodigo.ADMINISTRADOR.value,
            "cent_id": cent_id,
            "registrado_por": None,
        }
        return await repo.crear_usuario(datos)


async def _referencias() -> None:
    async with transaccion(None) as con:
        print("Centros de acopio (--centro-id):")
        for fila in await con.execute(
            text("SELECT cent_id, cent_descripcion FROM sigat.centro_acopio ORDER BY cent_id")
        ):
            print(f"  {fila.cent_id:>4}  {fila.cent_descripcion}")
        print("Municipios (los usa el formulario de usuarios para el productor):")
        for fila in await con.execute(
            text(
                "SELECT m.muni_id, m.muni_descripcion, d.depa_descripcion, d.depa_codigo || m.muni_codigo AS divipola"
                " FROM sigat.municipio m JOIN sigat.departamento d ON d.depa_id = m.depa_id"
                " ORDER BY d.depa_descripcion, m.muni_descripcion"
            )
        ):
            print(f"  {fila.muni_id:>4}  {fila.muni_descripcion} ({fila.depa_descripcion}) · {fila.divipola}")


async def _registrar_municipio(a: argparse.Namespace) -> None:
    """Dato de referencia (no es una cuenta). El catálogo DANE completo se carga aparte."""
    async with transaccion(None) as con:
        depa = await _id_departamento(con, a.departamento_codigo, a.departamento, a.region)
        muni = await con.scalar(
            text(
                "INSERT INTO sigat.municipio (muni_descripcion, depa_id, muni_codigo) VALUES (:n, :d, :c)"
                " ON CONFLICT (depa_id, muni_codigo) DO NOTHING RETURNING muni_id"
            ),
            {"n": a.nombre, "d": depa, "c": a.codigo},
        )
        print(
            f"Municipio {'registrado' if muni else 'ya existía'}: {a.departamento_codigo}{a.codigo} {a.nombre}."
        )


def _argumentos(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python -m sigat_api.cli", description="Administración de sigat-durazno-api"
    )
    sub = p.add_subparsers(dest="comando", required=True)

    i = sub.add_parser(
        "inicializar-admin", help="Crea el PRIMER administrador (solo si no hay ninguno activo)"
    )
    i.add_argument("--cedula", required=True, type=int)
    i.add_argument("--nombre", required=True)
    i.add_argument("--apellido", required=True)
    i.add_argument("--usuario", required=True, help="3 a 64 caracteres: letras, números, . _ @ -")
    i.add_argument("--correo")
    i.add_argument("--telefono")
    i.add_argument("--centro-id", type=int, help="Centro de acopio existente")
    i.add_argument("--centro", help="Nombre del centro de acopio (se crea si no existe)")
    i.add_argument("--departamento-codigo", help="Código DANE de 2 dígitos del departamento del centro")
    i.add_argument("--departamento", help="Nombre del departamento, si aún no está registrado")
    i.add_argument("--region", help="Región del departamento, si aún no está registrado")
    i.add_argument("--contrasena-stdin", action="store_true", help="Lee la contraseña de la entrada estándar")
    i.add_argument(
        "--entorno-produccion",
        action="store_true",
        help="Confirma que SIGAT_ENTORNO=produccion es intencional",
    )

    sub.add_parser("referencias", help="Lista centros de acopio y municipios con su id")

    m = sub.add_parser("registrar-municipio", help="Registra un municipio (dato de referencia DANE)")
    m.add_argument("--departamento-codigo", required=True)
    m.add_argument("--departamento", help="Nombre del departamento, si aún no está registrado")
    m.add_argument("--region")
    m.add_argument("--codigo", required=True, help="3 dígitos DANE del municipio")
    m.add_argument("--nombre", required=True)

    h = sub.add_parser("hash-contrasena", help="Imprime el hash argon2id de una contraseña")
    h.add_argument("--contrasena-stdin", action="store_true")
    return p.parse_args(argv)


async def _ejecutar(a: argparse.Namespace) -> None:
    crear_motor(obtener_configuracion())
    try:
        if a.comando == "inicializar-admin":
            usua_id = await inicializar_admin(a, _pedir_contrasena(a.contrasena_stdin))
            print(
                f"Administrador creado: id={usua_id}, usuario={a.usuario}. Ya puede iniciar sesión en la web."
            )
        elif a.comando == "referencias":
            await _referencias()
        elif a.comando == "registrar-municipio":
            await _registrar_municipio(a)
    finally:
        await cerrar_motor()


def main(argv: list[str] | None = None) -> None:
    a = _argumentos(argv)
    try:
        if a.comando == "hash-contrasena":
            print(contrasenas.generar_hash(_pedir_contrasena(a.contrasena_stdin)))
            return
        asyncio.run(_ejecutar(a))
    except ErrorComando as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
