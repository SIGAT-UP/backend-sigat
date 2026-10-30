-- =======================================================================
-- SIGAT v9 - AJUSTES INCREMENTALES SOBRE v8 (28/10/2026)
-- Origen: integración del backend único (ica-durazno-api) con la web y el móvil.
--
--   A1. Evidencia sincronizable: 'evidencia' entra en operacion_sync y se valida
--       que la operación sea de esa foto, de ese usuario y de ese dispositivo.
--   A2. Revisión del agrónomo: motivo de corrección en las tablas que la web corrige
--       y vista v_lectura_revision con el estado de cada lectura DERIVADO (no guardado).
--   A3. Administración de usuarios: unicidad real de usuario y correo, edición,
--       corrección de cédula, eliminación (física si no tiene actividad; si la tiene,
--       baja definitiva que conserva la historia) y productor creado por el administrador.
--   A4. Código de trampa: la BD ya lo valida (trampa_codigo_formato + fn_trampa_valida);
--       se añade fn_codigo_trampa_error para que backend y web den el mismo mensaje.
--
-- Una sola transacción. NO borra ni modifica filas existentes salvo A3.1, que solo
-- comprueba (y se detiene si hay duplicados que el responsable debe resolver antes).
-- =======================================================================
BEGIN;
SET LOCAL search_path = sigat, public;
SET LOCAL lock_timeout = '10s';

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_schema='sigat' AND table_name='planificacion_lote' AND column_name='plal_sync_id') THEN
    RAISE EXCEPTION 'Se requiere SIGAT v8 instalado (falta planificacion_lote.plal_sync_id)';
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_schema='sigat' AND table_name='usuario' AND column_name='usua_eliminado_en') THEN
    RAISE EXCEPTION 'Los ajustes v9 ya se aplicaron: no repita la migración';
  END IF;
END $$;

-- =======================================================================
-- A1. EVIDENCIA SINCRONIZABLE
-- v8: evidencia.oper_id es NOT NULL y UNIQUE y operacion_sync no admitía la entidad
-- 'evidencia'. La única forma era reutilizar la operación de la lectura (así lo hace la
-- demo), lo que permite UNA sola foto por lectura: la segunda no tenía operación válida.
-- v9 admite la operación propia de la foto y valida que ambas formas sean coherentes.
-- =======================================================================
ALTER TABLE sigat.operacion_sync DROP CONSTRAINT operacion_sync_entidad_valida;
ALTER TABLE sigat.operacion_sync ADD CONSTRAINT operacion_sync_entidad_valida
  CHECK (oper_entidad IN ('visita','lectura_trampa','aplicacion_fitosanitaria','cosecha',
                          'etapa_declarada','hallazgo','bpa_verificacion','manejo_agronomico',
                          'estimacion_produccion','planificacion_lote','evidencia'));

CREATE OR REPLACE FUNCTION sigat.fn_evidencia_operacion_valida() RETURNS trigger
LANGUAGE plpgsql SET search_path = sigat, public AS $$
DECLARE v_oper operacion_sync%ROWTYPE; v_arch_usua integer; v_oper_registro bigint;
BEGIN
  SELECT * INTO v_oper FROM operacion_sync WHERE oper_id = NEW.oper_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'La operación % no existe', NEW.oper_id USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF v_oper.oper_entidad = 'evidencia' THEN
    -- Forma v9 (recomendada): cada foto con su propia operación de alta.
    IF v_oper.oper_accion <> 'crear' OR v_oper.oper_registro_id IS DISTINCT FROM NEW.evid_id THEN
      RAISE EXCEPTION 'La operación % no es el alta de la evidencia %', NEW.oper_id, NEW.evid_id
        USING ERRCODE = 'integrity_constraint_violation';
    END IF;
  ELSE
    -- Forma v8 (compatibilidad): la foto viaja con la operación que creó el registro que respalda.
    -- Solo admite UNA foto por registro (evidencia.oper_id es único).
    IF NEW.lect_id IS NOT NULL THEN SELECT oper_id INTO v_oper_registro FROM lectura_trampa WHERE lect_id = NEW.lect_id;
    ELSIF NEW.hall_id IS NOT NULL THEN SELECT oper_id INTO v_oper_registro FROM hallazgo WHERE hall_id = NEW.hall_id;
    ELSIF NEW.visi_id IS NOT NULL THEN SELECT oper_id INTO v_oper_registro FROM visita WHERE visi_id = NEW.visi_id;
    END IF;
    IF v_oper_registro IS DISTINCT FROM NEW.oper_id THEN
      RAISE EXCEPTION 'La operación % no es la de la foto ni la del registro que respalda', NEW.oper_id
        USING ERRCODE = 'integrity_constraint_violation';
    END IF;
  END IF;
  IF v_oper.usua_id IS DISTINCT FROM NEW.usua_id OR v_oper.disp_id IS DISTINCT FROM NEW.disp_id THEN
    RAISE EXCEPTION 'La evidencia debe venir del mismo usuario y dispositivo que su operación'
      USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  SELECT usua_id INTO v_arch_usua FROM archivo_adjunto WHERE arch_id = NEW.arch_id;
  IF v_arch_usua IS NOT NULL AND v_arch_usua <> NEW.usua_id THEN
    RAISE EXCEPTION 'La foto pertenece a otro usuario' USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  RETURN NEW;
END $$;
COMMENT ON FUNCTION sigat.fn_evidencia_operacion_valida() IS
  'SIGAT v9 (A1): la evidencia se liga a SU operación (entidad evidencia, acción crear, registro = evid_id) o, por compatibilidad con v8, a la operación que creó la lectura/hallazgo/visita que respalda (una sola foto por registro). Siempre mismo usuario y dispositivo, y foto del mismo usuario. El binario puede llegar después (ADR-12).';
DROP TRIGGER IF EXISTS trg_evidencia_operacion_valida ON sigat.evidencia;
CREATE TRIGGER trg_evidencia_operacion_valida BEFORE INSERT ON sigat.evidencia
  FOR EACH ROW EXECUTE FUNCTION sigat.fn_evidencia_operacion_valida();

-- =======================================================================
-- A2. REVISIÓN DEL AGRÓNOMO
-- La BD revisa la VISITA (visi_estado_revision). Corregir o rechazar una lectura es
-- una versión nueva (append-only). Faltaba dónde guardar el MOTIVO de una corrección
-- (la anulación ya tenía *_motivo_anulacion).
-- =======================================================================
ALTER TABLE sigat.lectura_trampa ADD COLUMN lect_motivo_correccion varchar;
ALTER TABLE sigat.aplicacion_fitosanitaria ADD COLUMN apli_motivo_correccion varchar;
ALTER TABLE sigat.cosecha ADD COLUMN cose_motivo_correccion varchar;
ALTER TABLE sigat.lectura_trampa ADD CONSTRAINT lectura_trampa_motivo_correccion_version
  CHECK (lect_version > 1 OR lect_motivo_correccion IS NULL);
ALTER TABLE sigat.aplicacion_fitosanitaria ADD CONSTRAINT aplicacion_fitosanitaria_motivo_correccion_version
  CHECK (apli_version > 1 OR apli_motivo_correccion IS NULL);
ALTER TABLE sigat.cosecha ADD CONSTRAINT cosecha_motivo_correccion_version
  CHECK (cose_version > 1 OR cose_motivo_correccion IS NULL);
COMMENT ON COLUMN sigat.lectura_trampa.lect_motivo_correccion IS
  'SIGAT v9 (A2): motivo de la corrección (versión >= 2). El backend lo exige (>= 10 caracteres) cuando corrige el Agrónomo/Supervisor.';
COMMENT ON COLUMN sigat.aplicacion_fitosanitaria.apli_motivo_correccion IS 'SIGAT v9 (A2): motivo de la corrección (versión >= 2).';
COMMENT ON COLUMN sigat.cosecha.cose_motivo_correccion IS 'SIGAT v9 (A2): motivo de la corrección (versión >= 2).';

CREATE OR REPLACE VIEW sigat.v_lectura_revision AS
WITH ult AS (
  SELECT DISTINCT ON (lect_registro_id) *
  FROM lectura_trampa ORDER BY lect_registro_id, lect_version DESC
), ori AS (
  SELECT lect_registro_id, lect_especimenes AS especimenes_originales, usua_id AS usua_id_original
  FROM lectura_trampa WHERE lect_version = 1
)
SELECT ult.lect_registro_id, ult.lect_id, ult.lect_version, ult.visi_id, v.pred_id, ub.lote_id,
       ult.tram_id, t.tram_codigo, ult.lect_leida, ult.lect_especimenes, ori.especimenes_originales,
       ult.lect_t_observacion, ult.lect_t_sincronizacion, ult.lect_linaje,
       ori.usua_id_original, ult.usua_id AS usua_id_version,
       ult.lect_motivo_correccion, ult.lect_anulada, ult.lect_motivo_anulacion,
       v.visi_estado_revision, v.visi_revisada_por, v.visi_revisada_en,
       ult.lect_coincide_lote,
       CASE WHEN ult.lect_anulada                     THEN 'rechazado'
            WHEN ult.lect_linaje = 'autorreporte'     THEN 'autorreporte'
            WHEN ult.lect_version > 1                 THEN 'corregido'
            WHEN v.visi_estado_revision = 'aceptado'  THEN 'confirmado'
            ELSE 'sin_verificar' END AS estado_revision
FROM ult
JOIN ori ON ori.lect_registro_id = ult.lect_registro_id
JOIN visita v ON v.visi_id = ult.visi_id
JOIN trampa t ON t.tram_id = ult.tram_id
LEFT JOIN ubicacion_trampa ub ON ub.ubic_id = ult.ubic_id;
COMMENT ON VIEW sigat.v_lectura_revision IS
  'SIGAT v9 (A2): estado de revisión de CADA lectura, DERIVADO de sus versiones y de la revisión de su visita (no se guarda): rechazado (versión vigente anulada), autorreporte, corregido (versión >= 2), confirmado (visita aceptada) o sin_verificar. Web y móvil leen el mismo estado.';

-- =======================================================================
-- A3. ADMINISTRACIÓN DE USUARIOS
-- =======================================================================

-- A3.1 Unicidad real. El diccionario v8 decía "único sin distinguir mayúsculas" para
-- usua_usuario y pers_correo, pero ningún índice lo garantizaba.
DO $$ BEGIN
  IF EXISTS (SELECT lower(usua_usuario) FROM sigat.usuario GROUP BY 1 HAVING count(*) > 1) THEN
    RAISE EXCEPTION 'Hay nombres de usuario repetidos (sin distinguir mayúsculas): resuélvalos antes de aplicar v9';
  END IF;
  IF EXISTS (SELECT lower(pers_correo) FROM sigat.persona WHERE pers_correo IS NOT NULL GROUP BY 1 HAVING count(*) > 1) THEN
    RAISE EXCEPTION 'Hay correos repetidos (sin distinguir mayúsculas): resuélvalos antes de aplicar v9';
  END IF;
END $$;
CREATE UNIQUE INDEX ux_usuario_usuario_minusculas ON sigat.usuario (lower(usua_usuario));
CREATE UNIQUE INDEX ux_persona_correo_minusculas ON sigat.persona (lower(pers_correo)) WHERE pers_correo IS NOT NULL;

-- A3.2 Eliminación. Columnas de baja definitiva (la historia de campo nunca se borra).
ALTER TABLE sigat.usuario
  ADD COLUMN usua_eliminado_en timestamptz,
  ADD COLUMN usua_eliminado_por integer,
  ADD COLUMN usua_motivo_eliminacion varchar;
ALTER TABLE sigat.usuario
  ADD CONSTRAINT usuario_eliminado_por_fkey FOREIGN KEY (usua_eliminado_por) REFERENCES sigat.usuario (usua_id),
  ADD CONSTRAINT usuario_eliminacion_coherente CHECK (
    (usua_eliminado_en IS NULL AND usua_eliminado_por IS NULL AND usua_motivo_eliminacion IS NULL)
    OR (usua_eliminado_en IS NOT NULL AND usua_eliminado_por IS NOT NULL
        AND length(btrim(usua_motivo_eliminacion)) >= 10 AND usua_contrasena IS NULL));
COMMENT ON COLUMN sigat.usuario.usua_eliminado_en IS
  'SIGAT v9 (A3): baja DEFINITIVA de un usuario con actividad registrada. No inicia sesión, no aparece en listados, conserva su autoría en la historia. Nulo = vigente.';
COMMENT ON COLUMN sigat.usuario.usua_eliminado_por IS 'SIGAT v9 (A3): administrador que eliminó al usuario.';
COMMENT ON COLUMN sigat.usuario.usua_motivo_eliminacion IS 'SIGAT v9 (A3): motivo de la eliminación (>= 10 caracteres).';
CREATE INDEX ix_usuario_usua_eliminado_por ON sigat.usuario (usua_eliminado_por);

-- A3.3 Productor creado desde la web por el administrador: el técnico que lo registró
-- deja de ser obligatorio y se guarda el usuario que lo registró (cualquier rol).
ALTER TABLE sigat.productor ALTER COLUMN prod_tecnico_registro_id DROP NOT NULL;
ALTER TABLE sigat.productor ADD COLUMN prod_usua_registro_id integer;
ALTER TABLE sigat.productor
  ADD CONSTRAINT productor_usua_registro_id_fkey FOREIGN KEY (prod_usua_registro_id) REFERENCES sigat.usuario (usua_id),
  ADD CONSTRAINT productor_quien_registro CHECK (prod_tecnico_registro_id IS NOT NULL OR prod_usua_registro_id IS NOT NULL);
CREATE INDEX ix_productor_prod_usua_registro_id ON sigat.productor (prod_usua_registro_id);
COMMENT ON COLUMN sigat.productor.prod_tecnico_registro_id IS
  'Técnico que registró al productor en campo. Desde v9 es opcional: si lo crea el administrador en la web se usa prod_usua_registro_id.';
COMMENT ON COLUMN sigat.productor.prod_usua_registro_id IS
  'SIGAT v9 (A3): usuario (cualquier rol) que registró al productor. Al menos uno de los dos registradores es obligatorio.';

-- A3.4 Utilidades.
CREATE OR REPLACE FUNCTION sigat.fn_contar_referencias(p_tabla regclass, p_valor text, p_excluir text[] DEFAULT '{}')
RETURNS bigint LANGUAGE plpgsql STABLE SET search_path = sigat, public AS $$
DECLARE r record; n bigint; total bigint := 0;
BEGIN
  FOR r IN
    SELECT ns.nspname AS esquema, cl.relname AS tabla, a.attname AS columna
    FROM pg_constraint c
    JOIN pg_class cl ON cl.oid = c.conrelid
    JOIN pg_namespace ns ON ns.oid = cl.relnamespace
    JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]
    WHERE c.contype = 'f' AND c.confrelid = p_tabla AND array_length(c.conkey, 1) = 1
  LOOP
    -- p_excluir usa nombres calificados "esquema.tabla.columna"
    CONTINUE WHEN (r.esquema || '.' || r.tabla || '.' || r.columna) = ANY (p_excluir);
    EXECUTE format('SELECT count(*) FROM %I.%I WHERE %I::text = $1', r.esquema, r.tabla, r.columna) INTO n USING p_valor;
    total := total + n;
  END LOOP;
  RETURN total;
END $$;
COMMENT ON FUNCTION sigat.fn_contar_referencias(regclass, text, text[]) IS
  'SIGAT v9 (A3): cuenta las filas de TODAS las tablas que referencian por llave foránea a p_tabla con el valor dado (excepto las columnas "tabla.columna" de p_excluir). Genérica: una tabla nueva que referencie a usuario queda contemplada sin tocar esta función.';

CREATE OR REPLACE FUNCTION sigat.fn_usuario_tiene_actividad(p_usua integer)
RETURNS boolean LANGUAGE plpgsql STABLE SET search_path = sigat, public AS $$
DECLARE v_cc bigint; v_tecn integer; v_admi integer; n bigint;
BEGIN
  SELECT pers_cc INTO v_cc FROM usuario WHERE usua_id = p_usua;
  IF v_cc IS NULL THEN RETURN false; END IF;
  -- Lo que es "del usuario" y se borra con él no cuenta como actividad.
  n := fn_contar_referencias('sigat.usuario', p_usua::text, ARRAY[
         'sigat.perfil_usuario.usua_id', 'sigat.preferencia_notificacion.usua_id',
         'sigat.restablecimiento_clave.usua_id', 'sigat.notificacion.usua_id',
         'sigat.usuario_predio.usua_id']);
  IF n > 0 THEN RETURN true; END IF;
  SELECT tecn_id INTO v_tecn FROM tecnico WHERE pers_cc = v_cc;
  IF v_tecn IS NOT NULL AND fn_contar_referencias('sigat.tecnico', v_tecn::text) > 0 THEN RETURN true; END IF;
  SELECT admi_id INTO v_admi FROM administrador WHERE pers_cc = v_cc;
  IF v_admi IS NOT NULL AND fn_contar_referencias('sigat.administrador', v_admi::text) > 0 THEN RETURN true; END IF;
  IF EXISTS (SELECT 1 FROM productor WHERE pers_cc = v_cc)
     AND fn_contar_referencias('sigat.productor', v_cc::text) > 0 THEN RETURN true; END IF;
  IF fn_contar_referencias('sigat.persona', v_cc::text, ARRAY[
       'sigat.usuario.pers_cc', 'sigat.tecnico.pers_cc', 'sigat.administrador.pers_cc', 'sigat.productor.pers_cc']) > 0 THEN
    RETURN true;
  END IF;
  RETURN false;
END $$;
COMMENT ON FUNCTION sigat.fn_usuario_tiene_actividad(integer) IS
  'SIGAT v9 (A3): verdadero si algún registro del sistema (lecturas, visitas, planificaciones, bitácora, predios, trampas, rutas...) depende del usuario, de su persona o de su fila de rol. Decide si eliminar = borrar o = dar de baja.';

CREATE OR REPLACE FUNCTION sigat.fn_exigir_administrador(p_objetivo integer) RETURNS integer
LANGUAGE plpgsql STABLE SET search_path = sigat, public AS $$
DECLARE v_actor integer := fn_usuario_actual();
BEGIN
  IF v_actor IS NULL OR NOT EXISTS (
       SELECT 1 FROM usuario u JOIN rol r USING (rol_id) JOIN estado_registro e USING (esta_id)
       WHERE u.usua_id = v_actor AND r.rol_codigo = 'ADMINISTRADOR'
         AND e.esta_descripcion = 'activo' AND u.usua_eliminado_en IS NULL) THEN
    RAISE EXCEPTION 'Solo un administrador activo administra usuarios' USING ERRCODE = 'insufficient_privilege';
  END IF;
  IF p_objetivo = v_actor THEN
    RAISE EXCEPTION 'Un administrador no puede eliminarse ni cambiar su propia cédula' USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM usuario WHERE usua_id = p_objetivo) THEN
    RAISE EXCEPTION 'El usuario % no existe', p_objetivo USING ERRCODE = 'no_data_found';
  END IF;
  RETURN v_actor;
END $$;

-- A3.5 Eliminar usuario.
CREATE OR REPLACE FUNCTION sigat.fn_eliminar_usuario(p_usua integer, p_motivo text) RETURNS text
LANGUAGE plpgsql SET search_path = sigat, public AS $$
DECLARE v_actor integer; v_cc bigint; v_rol text; v_inactivo integer;
BEGIN
  v_actor := fn_exigir_administrador(p_usua);
  IF p_motivo IS NULL OR length(btrim(p_motivo)) < 10 THEN
    RAISE EXCEPTION 'Indique el motivo de la eliminación (mínimo 10 caracteres)' USING ERRCODE = 'check_violation';
  END IF;
  SELECT u.pers_cc, r.rol_codigo INTO v_cc, v_rol FROM usuario u JOIN rol r USING (rol_id)
   WHERE u.usua_id = p_usua AND u.usua_eliminado_en IS NULL;
  IF v_cc IS NULL THEN
    RAISE EXCEPTION 'El usuario ya fue eliminado' USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF v_rol = 'ADMINISTRADOR' AND NOT EXISTS (
       SELECT 1 FROM usuario u JOIN rol r USING (rol_id) JOIN estado_registro e USING (esta_id)
       WHERE r.rol_codigo = 'ADMINISTRADOR' AND e.esta_descripcion = 'activo'
         AND u.usua_eliminado_en IS NULL AND u.usua_id <> p_usua) THEN
    RAISE EXCEPTION 'No se puede eliminar al último administrador activo' USING ERRCODE = 'integrity_constraint_violation';
  END IF;

  IF NOT fn_usuario_tiene_actividad(p_usua) THEN
    -- Sin actividad: se borra de verdad (la bitácora registra el borrado con el actor).
    DELETE FROM perfil_usuario WHERE usua_id = p_usua;
    DELETE FROM preferencia_notificacion WHERE usua_id = p_usua;
    DELETE FROM restablecimiento_clave WHERE usua_id = p_usua;
    DELETE FROM notificacion WHERE usua_id = p_usua;
    DELETE FROM usuario_predio WHERE usua_id = p_usua;
    DELETE FROM usuario WHERE usua_id = p_usua;
    DELETE FROM tecnico WHERE pers_cc = v_cc;
    DELETE FROM administrador WHERE pers_cc = v_cc;
    DELETE FROM productor WHERE pers_cc = v_cc;
    DELETE FROM persona WHERE pers_cc = v_cc;
    RETURN 'eliminado';
  END IF;

  -- Con actividad: baja definitiva. Se conserva la fila para que la historia siga diciendo
  -- quién hizo qué; la cuenta queda sin contraseña, inactiva y sin predios vigentes.
  SELECT esta_id INTO STRICT v_inactivo FROM estado_registro WHERE esta_descripcion = 'inactivo';
  UPDATE usuario
     SET usua_eliminado_en = now(), usua_eliminado_por = v_actor, usua_motivo_eliminacion = btrim(p_motivo),
         usua_contrasena = NULL, usua_requiere_reinicio = (usua_proveedor = 'local'), esta_id = v_inactivo
   WHERE usua_id = p_usua;
  DELETE FROM usuario_predio WHERE usua_id = p_usua AND usup_desde >= CURRENT_DATE;
  UPDATE usuario_predio SET usup_hasta = CURRENT_DATE
   WHERE usua_id = p_usua AND (usup_hasta IS NULL OR usup_hasta > CURRENT_DATE);
  DELETE FROM restablecimiento_clave WHERE usua_id = p_usua AND rest_usado_en IS NULL;
  UPDATE tecnico SET esta_id = v_inactivo WHERE pers_cc = v_cc;
  UPDATE productor SET prod_activo = false WHERE pers_cc = v_cc;
  RETURN 'dado_de_baja';
END $$;
COMMENT ON FUNCTION sigat.fn_eliminar_usuario(integer, text) IS
  'SIGAT v9 (A3): elimina un usuario. Sin actividad registrada -> borrado físico de usuario, fila de rol y persona; devuelve ''eliminado''. Con actividad -> baja definitiva (usua_eliminado_en, sin contraseña, inactivo, predios cerrados), conservando la historia; devuelve ''dado_de_baja''. Solo un administrador activo, nunca a sí mismo ni al último administrador. Requiere sigat.usuario_actual.';

-- A3.6 Un usuario eliminado ya no cambia.
CREATE OR REPLACE FUNCTION sigat.fn_usuario_eliminado_inmutable() RETURNS trigger
LANGUAGE plpgsql SET search_path = sigat, public AS $$
BEGIN
  IF OLD.usua_eliminado_en IS NOT NULL THEN
    RAISE EXCEPTION 'El usuario % fue eliminado el %: no se modifica', OLD.usua_id, OLD.usua_eliminado_en
      USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
  RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS trg_usuario_eliminado_inmutable ON sigat.usuario;
CREATE TRIGGER trg_usuario_eliminado_inmutable BEFORE UPDATE OR DELETE ON sigat.usuario
  FOR EACH ROW EXECUTE FUNCTION sigat.fn_usuario_eliminado_inmutable();

-- A3.7 Corregir la cédula (llave de persona). Solo si nada externo depende de la persona.
CREATE OR REPLACE FUNCTION sigat.fn_corregir_cedula(p_usua integer, p_nueva bigint) RETURNS void
LANGUAGE plpgsql SET search_path = sigat, public AS $$
DECLARE v_vieja bigint; v_correo varchar;
BEGIN
  PERFORM fn_exigir_administrador(p_usua);
  SELECT pers_cc INTO v_vieja FROM usuario WHERE usua_id = p_usua AND usua_eliminado_en IS NULL;
  IF v_vieja IS NULL THEN
    RAISE EXCEPTION 'El usuario no existe o fue eliminado' USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF p_nueva IS NULL OR p_nueva <= 0 THEN
    RAISE EXCEPTION 'Cédula no válida' USING ERRCODE = 'check_violation';
  END IF;
  IF p_nueva = v_vieja THEN RETURN; END IF;
  IF EXISTS (SELECT 1 FROM persona WHERE pers_cc = p_nueva) THEN
    RAISE EXCEPTION 'Ya existe una persona con la cédula %', p_nueva USING ERRCODE = 'unique_violation';
  END IF;
  IF fn_contar_referencias('sigat.persona', v_vieja::text, ARRAY[
       'sigat.usuario.pers_cc','sigat.tecnico.pers_cc','sigat.administrador.pers_cc','sigat.productor.pers_cc']) > 0
     OR (EXISTS (SELECT 1 FROM productor WHERE pers_cc = v_vieja)
         AND fn_contar_referencias('sigat.productor', v_vieja::text) > 0) THEN
    RAISE EXCEPTION 'La cédula no se puede cambiar: hay predios o registros a nombre de esta persona'
      USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  INSERT INTO persona (pers_cc, pers_nombre, pers_apellido, pers_telefono, pers_direccion, pers_correo)
    SELECT p_nueva, pers_nombre, pers_apellido, pers_telefono, pers_direccion, NULL FROM persona WHERE pers_cc = v_vieja;
  UPDATE usuario SET pers_cc = p_nueva WHERE usua_id = p_usua;
  UPDATE tecnico SET pers_cc = p_nueva WHERE pers_cc = v_vieja;
  UPDATE administrador SET pers_cc = p_nueva WHERE pers_cc = v_vieja;
  UPDATE productor SET pers_cc = p_nueva WHERE pers_cc = v_vieja;
  -- el correo es único: se libera en la fila vieja y luego se pone en la nueva
  SELECT pers_correo INTO v_correo FROM persona WHERE pers_cc = v_vieja;
  DELETE FROM persona WHERE pers_cc = v_vieja;
  UPDATE persona SET pers_correo = v_correo WHERE pers_cc = p_nueva;
END $$;
COMMENT ON FUNCTION sigat.fn_corregir_cedula(integer, bigint) IS
  'SIGAT v9 (A3): corrige una cédula mal digitada (pers_cc es llave primaria). Solo si ningún predio, aplicación u otro registro depende de la persona; si dependen, la corrección es institucional. Requiere sigat.usuario_actual de un administrador.';

-- A3.8 Vista de administración de usuarios (lo que lista y edita la web).
CREATE OR REPLACE VIEW sigat.v_usuario_admin AS
SELECT u.usua_id, u.pers_cc, p.pers_nombre, p.pers_apellido,
       p.pers_nombre || ' ' || p.pers_apellido AS nombre_completo,
       p.pers_correo, p.pers_telefono, p.pers_direccion,
       u.usua_usuario, r.rol_codigo, r.rol_descripcion, u.usua_proveedor,
       (e.esta_descripcion = 'activo') AS activo, u.usua_ultimo_acceso, u.usua_requiere_reinicio,
       COALESCE(t.cent_id, a.cent_id) AS cent_id, t.tecn_codigo, pr.muni_id,
       (SELECT count(*) FROM usuario_predio up WHERE up.usua_id = u.usua_id AND up.usup_desde <= CURRENT_DATE
          AND (up.usup_hasta IS NULL OR up.usup_hasta > CURRENT_DATE)) AS predios_vigentes
FROM usuario u
JOIN persona p ON p.pers_cc = u.pers_cc
JOIN rol r ON r.rol_id = u.rol_id
JOIN estado_registro e ON e.esta_id = u.esta_id
LEFT JOIN tecnico t ON t.pers_cc = u.pers_cc
LEFT JOIN administrador a ON a.pers_cc = u.pers_cc
LEFT JOIN productor pr ON pr.pers_cc = u.pers_cc
WHERE u.usua_eliminado_en IS NULL;
COMMENT ON VIEW sigat.v_usuario_admin IS
  'SIGAT v9 (A3): usuarios vigentes (no eliminados) con persona, rol, estado y datos del rol, para la pantalla de usuarios del administrador. Si eliminar borrará o dará de baja se pregunta con fn_usuario_tiene_actividad(usua_id).';

-- El acceso a predios ignora a los usuarios eliminados.
CREATE OR REPLACE VIEW sigat.v_acceso_predio AS
SELECT up.usua_id, up.pred_id, u.rol_id, 'asignacion'::text AS origen
FROM usuario_predio up JOIN usuario u ON u.usua_id = up.usua_id
WHERE up.usup_desde <= CURRENT_DATE AND (up.usup_hasta IS NULL OR up.usup_hasta > CURRENT_DATE)
  AND u.usua_eliminado_en IS NULL
UNION
SELECT u.usua_id, p.pred_id, u.rol_id, 'propietario'::text
FROM predio p JOIN usuario u ON u.pers_cc = p.pers_cc
WHERE u.usua_eliminado_en IS NULL;

-- =======================================================================
-- A4. CÓDIGO DE TRAMPA: un único mensaje para backend y web
-- =======================================================================
CREATE OR REPLACE FUNCTION sigat.fn_codigo_trampa_error(p_codigo text, p_tipt_id integer) RETURNS text
LANGUAGE plpgsql STABLE SET search_path = sigat, public AS $$
DECLARE v_par text; v_num integer;
BEGIN
  IF p_codigo IS NULL OR p_codigo !~ '^[0-9]{5}-[0-9A-Za-z]{1,10}-[0-9]{1,4}$' THEN
    RETURN 'El código debe tener el formato Divipola-ruta-número, por ejemplo 54518-602-001';
  END IF;
  IF EXISTS (SELECT 1 FROM trampa WHERE tram_codigo = p_codigo) THEN
    RETURN 'Duplicidad de código de trampa: ' || p_codigo;
  END IF;
  SELECT tipt_paridad INTO v_par FROM tipo_trampa WHERE tipt_id = p_tipt_id;
  v_num := substring(p_codigo FROM '([0-9]+)$')::integer;
  IF v_par = 'impar' AND v_num % 2 = 0 THEN RETURN 'Una trampa Jackson lleva número impar (RN-005)'; END IF;
  IF v_par = 'par' AND v_num % 2 = 1 THEN RETURN 'Una trampa McPhail lleva número par (RN-005)'; END IF;
  RETURN NULL;
END $$;
COMMENT ON FUNCTION sigat.fn_codigo_trampa_error(text, integer) IS
  'SIGAT v9 (A4): devuelve el mensaje de error del código de trampa (formato, duplicado, paridad RN-005) o NULL si es válido. Mismas reglas que trampa_codigo_formato y fn_trampa_valida.';

COMMENT ON SCHEMA sigat IS
  'SIGAT v9 - evidencia sincronizable, revisión por versiones con motivo, administración de usuarios (edición, cédula, eliminación) sobre v8.';
COMMIT;
