-- SIGAT v9: validación estructural (sin datos). Debe terminar con NOTICE "VALIDACION V9 ESTRUCTURAL: OK".
SET search_path = sigat, public;
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='sigat.operacion_sync'::regclass
                 AND conname='operacion_sync_entidad_valida' AND pg_get_constraintdef(oid) LIKE '%evidencia%') THEN
    RAISE EXCEPTION 'operacion_sync no admite evidencia'; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='trg_evidencia_operacion_valida' AND NOT tgisinternal) THEN
    RAISE EXCEPTION 'Falta trg_evidencia_operacion_valida'; END IF;
  IF to_regclass('sigat.v_lectura_revision') IS NULL OR to_regclass('sigat.v_usuario_admin') IS NULL THEN
    RAISE EXCEPTION 'Faltan vistas v9'; END IF;
  IF to_regclass('sigat.ux_usuario_usuario_minusculas') IS NULL OR to_regclass('sigat.ux_persona_correo_minusculas') IS NULL THEN
    RAISE EXCEPTION 'Faltan índices de unicidad sin mayúsculas'; END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='sigat' AND table_name='usuario' AND column_name='usua_eliminado_en') THEN
    RAISE EXCEPTION 'Falta usuario.usua_eliminado_en'; END IF;
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='sigat' AND table_name='productor'
             AND column_name='prod_tecnico_registro_id' AND is_nullable='NO') THEN
    RAISE EXCEPTION 'productor.prod_tecnico_registro_id sigue siendo obligatorio'; END IF;
  IF to_regprocedure('sigat.fn_eliminar_usuario(integer,text)') IS NULL
     OR to_regprocedure('sigat.fn_corregir_cedula(integer,bigint)') IS NULL
     OR to_regprocedure('sigat.fn_codigo_trampa_error(text,integer)') IS NULL THEN
    RAISE EXCEPTION 'Faltan funciones v9'; END IF;
  RAISE NOTICE 'VALIDACION V9 ESTRUCTURAL: OK (no sustituye las pruebas funcionales)';
END $$;
