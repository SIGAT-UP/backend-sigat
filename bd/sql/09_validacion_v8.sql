-- Validaciones adicionales de la versión candidata (sin datos de demostración).
SET search_path = sigat, public;
DO $$ BEGIN
 IF to_regclass('sigat.planificacion_lote') IS NULL THEN RAISE EXCEPTION 'No existe planificacion_lote'; END IF;
 IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_schema='sigat' AND table_name='planificacion_lote'
                   AND column_name='plal_sync_id' AND is_nullable='NO') THEN
   RAISE EXCEPTION 'Falta identificador estable de planificacion_lote'; END IF;
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'sigat.operacion_sync'::regclass
  AND conname = 'operacion_sync_entidad_valida' AND pg_get_constraintdef(oid) LIKE '%planificacion_lote%') THEN
   RAISE EXCEPTION 'No se admite planificacion_lote en sync'; END IF;
 IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid = 'sigat.planificacion'::regclass
  AND tgname = 'trg_planificacion_respuesta_notifica' AND NOT tgisinternal) THEN
   RAISE EXCEPTION 'Falta disparador de notificaciones de respuesta'; END IF;
 IF EXISTS (SELECT 1 FROM sigat.planificacion_lote WHERE plal_sync_id IS NULL) THEN
   RAISE EXCEPTION 'Hay resultados sin UUID de sincronización'; END IF;
 RAISE NOTICE 'VALIDACION V8 ESTRUCTURAL: OK (no sustituye tests funcionales)';
END $$;
-- Avisos de calidad: resultados deben interpretarse y subsanarse antes de producción.
SELECT 'actividad_tecnico_historica_sin_origen' AS alerta, count(*) AS casos
  FROM sigat.planificacion p JOIN sigat.usuario u ON u.usua_id=p.usua_id_destinatario
  JOIN sigat.rol r ON r.rol_id=u.rol_id
  WHERE r.rol_codigo='TECNICO' AND p.plan_id_origen IS NULL;
SELECT 'actividad_resuelta_sin_operacion_offline' AS indicador, count(*) AS casos
  FROM sigat.planificacion_lote WHERE plal_estado <> 'pendiente' AND plal_oper_id IS NULL;
-- El segundo indicador no es error: resultados online anteriores y capturas online legítimas no usan operacion_sync.
