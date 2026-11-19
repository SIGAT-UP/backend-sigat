-- =====================================================================
-- SIGAT v9.1 - Ampliación de v_planificacion (F4/F5, ET §3.2.8) — revisión Alembic 0010
-- Necesita: 01 a 18. Idempotente (CREATE OR REPLACE). Conserva las 24 columnas de 03_vistas.sql
-- en el mismo orden y agrega 7 al final; no crea ni modifica tablas ni datos.
-- plan_motivo_rechazo (ET la toma de la tabla, donde no existe) se deriva de plan_observacion_respuesta, que el
-- CHECK planificacion_rechazo_con_observacion vuelve obligatoria como motivo solo al rechazar.
-- =====================================================================

CREATE OR REPLACE VIEW sigat.v_planificacion AS
SELECT p.plan_id, p.plan_actividad, p.plan_fecha_inicio, p.plan_fecha_fin, p.plan_hora_desde, p.plan_hora_hasta,
       p.plan_estado, p.plan_observaciones, p.plan_observacion_respuesta, p.plan_creada_en, p.plan_respondida_en,
       p.usua_id_destinatario, pd.pers_nombre || ' ' || pd.pers_apellido AS destinatario, rd.rol_descripcion AS rol_destinatario,
       p.usua_id_creador, pc.pers_nombre || ' ' || pc.pers_apellido AS creador,
       a.arch_nombre_original AS documento,
       COALESCE((SELECT array_agg(l.lote_codigo ORDER BY l.lote_codigo) FROM sigat.planificacion_lote pl
                  JOIN sigat.lote l USING (lote_id) WHERE pl.plan_id = p.plan_id), '{}') AS lotes,
       p.plan_id_origen, p.usua_id_respuesta, pr.pers_nombre || ' ' || pr.pers_apellido AS respondio,
       (SELECT count(*) FROM sigat.planificacion_lote x WHERE x.plan_id = p.plan_id AND x.plal_estado = 'pendiente')    AS lotes_pendientes,
       (SELECT count(*) FROM sigat.planificacion_lote x WHERE x.plan_id = p.plan_id AND x.plal_estado = 'ejecutada')    AS lotes_ejecutados,
       (SELECT count(*) FROM sigat.planificacion_lote x WHERE x.plan_id = p.plan_id AND x.plal_estado = 'no_ejecutada') AS lotes_no_ejecutados,
       p.arch_id_documento, p.plan_documento_clase,
       a.arch_mime AS documento_mime,
       a.arch_tamano_bytes AS documento_bytes,
       a.arch_paginas AS documento_paginas,
       COALESCE((SELECT array_agg(l.lote_descripcion ORDER BY l.lote_codigo) FROM sigat.planificacion_lote pl
                  JOIN sigat.lote l USING (lote_id) WHERE pl.plan_id = p.plan_id), '{}') AS lotes_descripcion,
       CASE WHEN p.plan_estado = 'rechazada' THEN p.plan_observacion_respuesta END AS plan_motivo_rechazo
FROM sigat.planificacion p
JOIN sigat.usuario ud ON ud.usua_id = p.usua_id_destinatario JOIN sigat.persona pd ON pd.pers_cc = ud.pers_cc JOIN sigat.rol rd ON rd.rol_id = ud.rol_id
JOIN sigat.usuario uc ON uc.usua_id = p.usua_id_creador JOIN sigat.persona pc ON pc.pers_cc = uc.pers_cc
LEFT JOIN sigat.usuario ur ON ur.usua_id = p.usua_id_respuesta LEFT JOIN sigat.persona pr ON pr.pers_cc = ur.pers_cc
LEFT JOIN sigat.archivo_adjunto a ON a.arch_id = p.arch_id_documento;

COMMENT ON VIEW sigat.v_planificacion IS 'Planificación con nombres de destinatario/creador, de quien respondió, documento adjunto y lotes: forma que consume el modelo Planning del frontend. plan_id_origen distingue la actividad de un técnico (apunta a la planificación aprobada por el productor) de la planificación del productor (nulo); los contadores resumen el resultado por lote. F4/F5 (0010): referencia, clase, tipo, tamaño y páginas del documento, descripción de los lotes (mismo orden que lotes) y motivo del rechazo.';
