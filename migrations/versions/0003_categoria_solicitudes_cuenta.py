"""SIGAT v9.1: categoría de aviso «solicitudes_cuenta».

Qué hace: ejecuta ``bd/sql/12_ajustes_v9_1.sql``, que SOLO AGREGA un valor al catálogo
``categoria_notificacion`` (idempotente: si ya existe, no hace nada).
Por qué: las solicitudes de «¿Problemas para ingresar?» llegan como aviso de esta categoría a
cada administrador activo, que asigna la contraseña nueva desde Usuarios.
Riesgo: ninguno sobre datos existentes. ``downgrade`` no borra el valor (puede tener avisos
asociados).

Revisión: 0003
"""

from pathlib import Path

from alembic import op
from sqlalchemy.util import await_only

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

ARCHIVO = Path(__file__).resolve().parents[2] / "bd" / "sql" / "12_ajustes_v9_1.sql"


def upgrade() -> None:
    crudo = op.get_bind().connection.driver_connection
    await_only(crudo.execute(ARCHIVO.read_text(encoding="utf-8")))  # type: ignore[union-attr]


def downgrade() -> None:
    """Sin cambios: el valor de catálogo puede estar referenciado por avisos."""
