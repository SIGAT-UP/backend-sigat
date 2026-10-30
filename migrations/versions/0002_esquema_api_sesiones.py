"""Esquema ``api``: tablas técnicas del backend que la BD SIGAT no tiene.

* api.sesion_refresco: tokens de refresco rotativos (solo hash).
* api.intento_login: limitación de intentos por usuario/IP.

Revisión: 0002
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS api")
    op.create_table(
        "sesion_refresco",
        sa.Column("sesr_id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("usua_id", sa.Integer, sa.ForeignKey("sigat.usuario.usua_id"), nullable=False),
        sa.Column("disp_id", pg.UUID, sa.ForeignKey("sigat.dispositivo.disp_id"), nullable=False),
        sa.Column(
            "sesr_familia", pg.UUID, nullable=False, comment="Cadena de rotación; reuso = revocar familia."
        ),
        sa.Column(
            "sesr_hash",
            sa.CHAR(64),
            nullable=False,
            unique=True,
            comment="SHA-256 del token; nunca el token.",
        ),
        sa.Column("sesr_cliente", sa.String(10), nullable=False),
        sa.Column("sesr_creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("sesr_expira_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sesr_usado_en", sa.DateTime(timezone=True)),
        sa.Column("sesr_revocado_en", sa.DateTime(timezone=True)),
        sa.CheckConstraint("sesr_cliente IN ('web','movil')", name="sesion_refresco_cliente_valido"),
        schema="api",
    )
    op.create_index("ix_sesion_refresco_usuario", "sesion_refresco", ["usua_id", "disp_id"], schema="api")
    op.create_table(
        "intento_login",
        sa.Column("inte_id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("inte_clave", sa.String(300), nullable=False, comment="usuario normalizado o IP."),
        sa.Column("inte_exito", sa.Boolean, nullable=False),
        sa.Column("inte_t", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema="api",
    )
    op.create_index("ix_intento_login_clave_t", "intento_login", ["inte_clave", "inte_t"], schema="api")


def downgrade() -> None:
    op.drop_table("intento_login", schema="api")
    op.drop_table("sesion_refresco", schema="api")
