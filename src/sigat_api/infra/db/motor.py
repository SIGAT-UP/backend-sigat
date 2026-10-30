"""Motor asíncrono único hacia la BD SIGAT v9 (PostgreSQL 16 + PostGIS).

Reglas de conexión (README de la BD v9):
* Usuario de APLICACIÓN (no superusuario, no dueño del esquema).
* ``search_path = sigat, public`` en cada conexión.
* ``statement_timeout`` acotado: el servidor tolera 60 s por operación (RNF-008),
  pero ninguna consulta de lectura debe acercarse a eso.
"""

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from sigat_api.config import Configuracion

_motor: AsyncEngine | None = None


def crear_motor(cfg: Configuracion) -> AsyncEngine:
    global _motor
    if _motor is None:
        _motor = create_async_engine(
            cfg.db_url,
            pool_size=cfg.db_pool_tamano,
            max_overflow=cfg.db_pool_extra,
            pool_pre_ping=True,
            connect_args={
                "server_settings": {
                    "search_path": f"{cfg.db_esquema}, public",
                    "statement_timeout": str(cfg.db_timeout_sentencia_ms),
                    "application_name": "sigat-durazno-api",
                    "timezone": "UTC",
                }
            },
        )
    return _motor


def obtener_motor() -> AsyncEngine:
    if _motor is None:
        raise RuntimeError("El motor de BD no se ha creado. Llame a crear_motor() al iniciar la app.")
    return _motor


async def cerrar_motor() -> None:
    global _motor
    if _motor is not None:
        await _motor.dispose()
        _motor = None
