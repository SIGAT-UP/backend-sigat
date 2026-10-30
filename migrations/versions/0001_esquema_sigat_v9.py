"""Línea base: esquema institucional SIGAT v9 (archivos de ``bd/sql``).

Qué hace y por qué
------------------
* **Base vacía** (sin tablas en el esquema ``sigat``): ejecuta, en orden, los archivos del
  paquete de BD SIGAT v9 copiados en ``bd/sql`` (esquema, catálogos básicos, vistas, funciones,
  ajustes v8 y v9 con sus validaciones). Así ``alembic upgrade head`` construye la base completa
  desde cero. **No crea cuentas de usuario ni datos de demostración.**
* **Base que ya tiene SIGAT v9** (instalada con ``psql -f bd/sql/00_instalar_todo.sql`` o por el
  equipo de BD): no cambia nada; solo queda registrada en ``api.alembic_version``.
* **Base con otra versión** (p. ej. v8): se DETIENE sin modificar nada. La actualización v8 → v9
  la aplica quien administra la base con ``migracion/M8_v8_a_v9.sql`` del paquete de BD, después
  de un respaldo; luego se vuelve a ejecutar ``alembic upgrade head``.

Todo ocurre en UNA transacción: si un archivo falla, no queda nada a medias.
``downgrade`` no borra el esquema institucional (operación destructiva: se hace a mano y con
revisión). La primera vez requiere un usuario que pueda crear las extensiones ``postgis`` y
``btree_gist`` (en desarrollo, el de docker compose).

Revisión: 0001
"""

from pathlib import Path

from alembic import op
from sqlalchemy import text
from sqlalchemy.util import await_only

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

CARPETA_SQL = Path(__file__).resolve().parents[2] / "bd" / "sql"
# Mismo orden que bd/sql/00_instalar_todo.sql. 06_validacion.sql se omite: solo muestra
# consultas para revisión humana con comandos de psql (\echo).
ARCHIVOS = (
    "01_esquema_completo.sql",
    "02_catalogos_basicos.sql",
    "03_vistas.sql",
    "04_funciones.sql",
    "08_ajustes_v8.sql",
    "09_validacion_v8.sql",
    "10_ajustes_v9.sql",
    "11_validacion_v9.sql",
)


def _contenido(nombre: str) -> str:
    """Texto del archivo sin sus BEGIN/COMMIT propios (aquí corre dentro de la transacción de
    Alembic) ni comandos de psql."""
    lineas = (CARPETA_SQL / nombre).read_text(encoding="utf-8").splitlines()
    return "\n".join(
        linea for linea in lineas if linea.strip() not in ("BEGIN;", "COMMIT;") and not linea.startswith("\\")
    )


def upgrade() -> None:
    con = op.get_bind()
    tablas = con.execute(text("SELECT count(*) FROM pg_tables WHERE schemaname = 'sigat'")).scalar()
    if not tablas:
        crudo = con.connection.driver_connection  # asyncpg: admite varias sentencias por llamada
        for nombre in ARCHIVOS:
            await_only(crudo.execute(_contenido(nombre)))  # type: ignore[union-attr]
        return
    es_v9 = con.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = 'sigat' AND table_name = 'usuario' AND column_name = 'usua_eliminado_en'"
        )
    ).scalar()
    if not es_v9:
        raise RuntimeError(
            "La base tiene el esquema SIGAT pero no es v9. Haga un respaldo y aplique "
            "migracion/M8_v8_a_v9.sql del paquete de BD; luego vuelva a ejecutar alembic upgrade head."
        )


def downgrade() -> None:
    """No se borra el esquema institucional desde aquí (sería destructivo)."""
