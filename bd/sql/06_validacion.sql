-- =====================================================================
-- SIGAT v7 - VALIDACIÓN DEL ESQUEMA
-- Cada consulta debe devolver 0 filas (la primera, 74 en "tablas").
-- Ejecutar después de 01_esquema_completo.sql: psql -f 06_validacion.sql
-- =====================================================================
SET search_path = sigat, public;

\echo '== 0. Número de tablas del esquema (esperado: 74)'
SELECT count(*) AS tablas FROM pg_tables WHERE schemaname = 'sigat';

\echo '== 1. Tablas sin clave primaria (esperado: 0 filas)'
SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'sigat' AND c.relkind = 'r'
  AND NOT EXISTS (SELECT 1 FROM pg_constraint k WHERE k.conrelid = c.oid AND k.contype = 'p');

\echo '== 2. Llaves foráneas sin índice que las respalde (esperado: 0 filas)'
SELECT k.conrelid::regclass AS tabla, k.conname
FROM pg_constraint k
WHERE k.contype = 'f' AND k.connamespace = 'sigat'::regnamespace
  AND NOT EXISTS (
    SELECT 1 FROM pg_index i
    WHERE i.indrelid = k.conrelid
      AND (i.indkey::int2[])[0:cardinality(k.conkey) - 1] = k.conkey);

\echo '== 3. Tablas sin comentario (esperado: 0 filas)'
SELECT c.relname FROM pg_class c
WHERE c.relnamespace = 'sigat'::regnamespace AND c.relkind = 'r' AND obj_description(c.oid, 'pg_class') IS NULL;

\echo '== 4. Columnas sin comentario (esperado: 0 filas)'
SELECT c.relname, a.attname FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid
WHERE c.relnamespace = 'sigat'::regnamespace AND c.relkind = 'r' AND a.attnum > 0 AND NOT a.attisdropped
  AND col_description(c.oid, a.attnum) IS NULL;

\echo '== 5. Regla del prefijo de 4 letras: columnas cuyo prefijo no es el de ninguna tabla (esperado: 0 filas)'
SELECT c.relname, a.attname
FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid
WHERE c.relnamespace = 'sigat'::regnamespace AND c.relkind = 'r' AND a.attnum > 0 AND NOT a.attisdropped
  AND split_part(a.attname, '_', 1) <> ALL (ARRAY['admi', 'apli', 'arbo', 'arch', 'atra', 'bita', 'bpav', 'cate', 'cent', 'conc', 'cond', 'cose', 'crit', 'depa', 'disp', 'esce', 'espc', 'espm', 'esta', 'esti', 'etap', 'evid', 'feno', 'fenr', 'hall', 'imag', 'indi', 'indm', 'lect', 'loca', 'lote', 'lotg', 'mane', 'muni', 'norm', 'noti', 'oper', 'paqu', 'perf', 'peri', 'perm', 'pers', 'plag', 'plan', 'plal', 'pred', 'pref', 'prof', 'prod', 'proc', 'prog', 'prou', 'rang', 'rece', 'regi', 'rest', 'reti', 'retc', 'rol', 'rolp', 'ruta', 'seve', 'tecn', 'tipm', 'tipt', 'tram', 'ubic', 'unid', 'usua', 'usup', 'vari', 'vigi', 'visi', 'visl']);

\echo '== 6. Rastros de ICA en nombres de columnas o comentarios (esperado: 0 filas)'
SELECT c.relname, a.attname FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid
WHERE c.relnamespace = 'sigat'::regnamespace AND c.relkind = 'r' AND a.attnum > 0
  AND (a.attname ~* '(^|_)ica(_|$)' OR col_description(c.oid, a.attnum) ~ '\mICA\M')
UNION ALL
SELECT c.relname, '(tabla)' FROM pg_class c
WHERE c.relnamespace = 'sigat'::regnamespace AND c.relkind = 'r' AND obj_description(c.oid, 'pg_class') ~ '\mICA\M';

\echo '== 7. Tablas de solo inserción sin disparador de bloqueo (esperado: 0 filas)'
SELECT t FROM unnest(ARRAY['aplicacion_fitosanitaria','bitacora_auditoria','bpa_verificacion','concepto_aptitud','cosecha',
  'estimacion_produccion','etapa_declarada','evidencia','hallazgo','indice_mtd_lectura','indice_mtd','lectura_trampa',
  'manejo_agronomico','operacion_sync','recepcion_sync','visita_lote']) AS t
WHERE NOT EXISTS (SELECT 1 FROM pg_trigger g WHERE g.tgrelid = ('sigat.' || t)::regclass AND g.tgname = 'trg_' || t || '_ro');

\echo '== 8. Geometrías con índice espacial (esperado: 0 filas sin índice)'
SELECT c.relname, a.attname FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid
WHERE c.relnamespace = 'sigat'::regnamespace AND c.relkind = 'r' AND a.attnum > 0 AND NOT a.attisdropped
  AND format_type(a.atttypid, a.atttypmod) LIKE 'geometry%'
  AND NOT EXISTS (SELECT 1 FROM pg_index i JOIN pg_class ic ON ic.oid = i.indexrelid JOIN pg_am am ON am.oid = ic.relam
                  WHERE i.indrelid = c.oid AND am.amname = 'gist' AND a.attnum = ANY (i.indkey::int2[]));

\echo '== 9. Actividades de técnico sin planificación de origen aprobada (esperado: 0 filas)'
SELECT t.plan_id FROM planificacion t
JOIN usuario u ON u.usua_id = t.usua_id_destinatario JOIN rol r ON r.rol_id = u.rol_id AND r.rol_codigo = 'TECNICO'
LEFT JOIN planificacion o ON o.plan_id = t.plan_id_origen
WHERE o.plan_id IS NULL OR o.plan_estado NOT IN ('aceptada', 'completada');

\echo '== 10. Planificaciones respondidas sin quién respondió (esperado: 0 filas)'
SELECT plan_id FROM planificacion WHERE (plan_estado IN ('aceptada', 'rechazada')) AND usua_id_respuesta IS NULL;

\echo '== 11. Lotes resueltos sin fecha de resolución, o no ejecutados sin justificación (esperado: 0 filas)'
SELECT plan_id, lote_id FROM planificacion_lote
WHERE (plal_estado <> 'pendiente' AND plal_resuelta_en IS NULL)
   OR (plal_estado = 'no_ejecutada' AND coalesce(btrim(plal_observacion), '') = '');

\echo '== 12. Evidencias que no apuntan a exactamente un origen (esperado: 0 filas)'
SELECT evid_id FROM evidencia WHERE num_nonnulls(lect_id, hall_id, visi_id, plan_id) <> 1;

\echo '== 13. Archivos almacenados sin referencia externa o sin hash (esperado: 0 filas)'
SELECT arch_id FROM archivo_adjunto WHERE arch_estado = 'almacenado' AND (arch_ref_almacenamiento IS NULL OR arch_hash_sha256 IS NULL);
