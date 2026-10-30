"""Entorno de Alembic. Lee la URL de ``SIGAT_DB_URL`` (nunca de alembic.ini)."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from sigat_api.config import obtener_configuracion

if context.config.config_file_name is not None:
    fileConfig(context.config.config_file_name)


def _ejecutar(conexion) -> None:  # type: ignore[no-untyped-def]
    context.configure(connection=conexion, version_table_schema="api", include_schemas=True)
    with context.begin_transaction():
        context.run_migrations()


async def _en_linea() -> None:
    motor = create_async_engine(obtener_configuracion().db_url)
    async with motor.begin() as con:
        await con.execute(text("CREATE SCHEMA IF NOT EXISTS api"))
        await con.run_sync(_ejecutar)
    await motor.dispose()


if context.is_offline_mode():
    raise SystemExit("Use el modo en línea: alembic upgrade head")
asyncio.run(_en_linea())
