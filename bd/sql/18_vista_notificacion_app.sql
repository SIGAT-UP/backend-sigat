-- =====================================================================
-- SIGAT v9.1 - Vista de la bandeja de avisos (F6, ET §3.2.7) — revisión Alembic 0009
-- Necesita: 01 a 17. Idempotente (CREATE OR REPLACE). Solo agrega una vista.
-- No es un mecanismo de autorización: el backend la lee siempre filtrando por el usua_id del token.
-- =====================================================================

CREATE OR REPLACE VIEW sigat.v_notificacion_app AS
SELECT n.noti_id, n.usua_id, n.noti_titulo, n.noti_cuerpo,
       n.noti_destino_ruta, n.noti_destino_argumento,
       n.noti_creada_en, n.noti_leida_en,
       c.cate_codigo, c.cate_descripcion,
       (n.noti_leida_en IS NULL) AS no_leida
FROM sigat.notificacion n
JOIN sigat.categoria_notificacion c USING (cate_id);

COMMENT ON VIEW sigat.v_notificacion_app IS 'F6 (PW06b, P06-P): avisos con su categoría y el indicador no_leida. Devuelve todas las filas; filtrar por usua_id.';
