"""Vista de la bandeja de avisos ``v_notificacion_app`` (F6, ET §3.2.7).

Ejecuta ``bd/sql/18_vista_notificacion_app.sql``: solo agrega la vista, sin tocar tablas ni datos.
``downgrade`` elimina únicamente esa vista.

Revisión: 0009
"""

from pathlib import Path

from alembic import op
from sqlalchemy.util import await_only

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

ARCHIVO = Path(__file__).resolve().parents[2] / "bd" / "sql" / "18_vista_notificacion_app.sql"
VISTA = "sigat.v_notificacion_app"


def upgrade() -> None:
    crudo = op.get_bind().connection.driver_connection
    await_only(crudo.execute(ARCHIVO.read_text(encoding="utf-8")))  # type: ignore[union-attr]


def downgrade() -> None:
    op.execute(f"DROP VIEW IF EXISTS {VISTA}")
