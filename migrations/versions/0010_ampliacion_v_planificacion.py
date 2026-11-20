"""Ampliación de ``v_planificacion`` (F4/F5, ET §3.2.8).

Ejecuta ``bd/sql/19_ampliacion_v_planificacion.sql``: conserva las columnas actuales y agrega siete
al final. ``downgrade`` restaura la definición de ``03_vistas.sql`` (revisión 0001); debe borrar la
vista porque PostgreSQL no permite quitar columnas con ``CREATE OR REPLACE``.

Revisión: 0010
"""

from pathlib import Path

from alembic import op
from sqlalchemy.util import await_only

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

ARCHIVO = Path(__file__).resolve().parents[2] / "bd" / "sql" / "19_ampliacion_v_planificacion.sql"

VISTA_ANTERIOR = """
SET LOCAL search_path = sigat, public;
CREATE VIEW v_planificacion AS
SELECT p.plan_id, p.plan_actividad, p.plan_fecha_inicio, p.plan_fecha_fin, p.plan_hora_desde, p.plan_hora_hasta,
       p.plan_estado, p.plan_observaciones, p.plan_observacion_respuesta, p.plan_creada_en, p.plan_respondida_en,
       p.usua_id_destinatario, pd.pers_nombre || ' ' || pd.pers_apellido AS destinatario, rd.rol_descripcion AS rol_destinatario,
       p.usua_id_creador, pc.pers_nombre || ' ' || pc.pers_apellido AS creador,
       a.arch_nombre_original AS documento,
       COALESCE((SELECT array_agg(l.lote_codigo ORDER BY l.lote_codigo) FROM planificacion_lote pl
                  JOIN lote l USING (lote_id) WHERE pl.plan_id = p.plan_id), '{}') AS lotes,
       p.plan_id_origen, p.usua_id_respuesta, pr.pers_nombre || ' ' || pr.pers_apellido AS respondio,
       (SELECT count(*) FROM planificacion_lote x WHERE x.plan_id = p.plan_id AND x.plal_estado = 'pendiente')    AS lotes_pendientes,
       (SELECT count(*) FROM planificacion_lote x WHERE x.plan_id = p.plan_id AND x.plal_estado = 'ejecutada')    AS lotes_ejecutados,
       (SELECT count(*) FROM planificacion_lote x WHERE x.plan_id = p.plan_id AND x.plal_estado = 'no_ejecutada') AS lotes_no_ejecutados
FROM planificacion p
JOIN usuario ud ON ud.usua_id = p.usua_id_destinatario JOIN persona pd ON pd.pers_cc = ud.pers_cc JOIN rol rd ON rd.rol_id = ud.rol_id
JOIN usuario uc ON uc.usua_id = p.usua_id_creador JOIN persona pc ON pc.pers_cc = uc.pers_cc
LEFT JOIN usuario ur ON ur.usua_id = p.usua_id_respuesta LEFT JOIN persona pr ON pr.pers_cc = ur.pers_cc
LEFT JOIN archivo_adjunto a ON a.arch_id = p.arch_id_documento;
COMMENT ON VIEW v_planificacion IS 'Planificación con nombres de destinatario/creador, de quien respondió, documento adjunto y lotes: forma que consume el modelo Planning del frontend. plan_id_origen distingue la actividad de un técnico (apunta a la planificación aprobada por el productor) de la planificación del productor (nulo); los contadores resumen el resultado por lote.';
"""


def upgrade() -> None:
    crudo = op.get_bind().connection.driver_connection
    await_only(crudo.execute(ARCHIVO.read_text(encoding="utf-8")))  # type: ignore[union-attr]


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS sigat.v_planificacion")
    crudo = op.get_bind().connection.driver_connection
    await_only(crudo.execute(VISTA_ANTERIOR))  # type: ignore[union-attr]
