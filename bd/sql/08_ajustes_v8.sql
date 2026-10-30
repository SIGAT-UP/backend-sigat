-- =======================================================================
-- SIGAT v8 CANDIDATA - AJUSTES INCREMENTALES SOBRE v7
-- Fuente: reuniones y auditoría comparativa v6-v7, octubre 2026.
-- Compatible con instalación v7 o migración v7 -> v8.
-- NO ejecutar sobre producción sin respaldo y validación del responsable.
-- NO modifica ni borra filas existentes. No implica elección del stack UI/API.
-- =======================================================================
BEGIN;
SET LOCAL search_path = sigat, public;
SET LOCAL lock_timeout = '10s';

DO $$ BEGIN
  IF to_regclass('sigat.planificacion') IS NULL OR to_regclass('sigat.operacion_sync') IS NULL THEN
    RAISE EXCEPTION 'Se requiere el esquema SIGAT v7 instalado en sigat';
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_schema='sigat' AND table_name='planificacion_lote'
                   AND column_name='plal_sync_id') THEN
    RAISE EXCEPTION 'Los ajustes v8 ya se aplicaron: no repita la migración';
  END IF;
END $$;

-- P1. Cada asociación plan-lote tiene un UUID duradero para el circuito offline.
-- Esto no cambia la PK compuesta; la identifica adicionalmente desde un cliente.
ALTER TABLE sigat.planificacion_lote
  ADD COLUMN plal_sync_id uuid NOT NULL DEFAULT gen_random_uuid(),
  ADD COLUMN plal_oper_id bigint;
ALTER TABLE sigat.planificacion_lote
  ADD CONSTRAINT planificacion_lote_sync_id_unico UNIQUE (plal_sync_id),
  ADD CONSTRAINT planificacion_lote_oper_id_unico UNIQUE (plal_oper_id),
  ADD CONSTRAINT planificacion_lote_oper_id_fkey FOREIGN KEY (plal_oper_id) REFERENCES sigat.operacion_sync(oper_id),
  ADD CONSTRAINT planificacion_lote_oper_resultado CHECK (plal_oper_id IS NULL OR plal_estado <> 'pendiente');
-- UNIQUE(plal_oper_id) ya crea su índice; evitamos un índice duplicado.
COMMENT ON COLUMN sigat.planificacion_lote.plal_sync_id IS
  'Identificador estable UUID del resultado por lote para sincronización offline; la clave lógica original sigue siendo (plan_id,lote_id).';
COMMENT ON COLUMN sigat.planificacion_lote.plal_oper_id IS
  'Operación offline vinculada al resultado; NULL si se registró sin operacion_sync. Requiere consistencia de entidad, registro y usuario.';

-- P2. Ampliación del catálogo tipado: la entidad de resultado de un lote.
ALTER TABLE sigat.operacion_sync DROP CONSTRAINT operacion_sync_entidad_valida;
ALTER TABLE sigat.operacion_sync ADD CONSTRAINT operacion_sync_entidad_valida
  CHECK (oper_entidad IN ('visita','lectura_trampa','aplicacion_fitosanitaria',
                         'cosecha','etapa_declarada','hallazgo','bpa_verificacion',
                         'manejo_agronomico','estimacion_produccion','planificacion_lote'));

-- P3. Refuerzo de autoría y validación de resultados offline.
CREATE OR REPLACE FUNCTION fn_planificacion_valida() RETURNS trigger LANGUAGE plpgsql SET search_path = sigat, public AS $$
DECLARE v_rol_creador text; v_rol_dest text; v_rol_origen text; v_actor integer := fn_usuario_actual(); o planificacion%ROWTYPE;
BEGIN
  SELECT r.rol_codigo INTO v_rol_dest FROM usuario u JOIN rol r USING (rol_id) WHERE u.usua_id = NEW.usua_id_destinatario;
  IF TG_OP = 'INSERT' THEN
    -- Defensa en profundidad: el actor no puede atribuir una propuesta a otro usuario.
    -- IMPORTANTE: el backend debe fijar sigat.usuario_actual desde una sesión AUTENTICADA.
    IF v_actor IS DISTINCT FROM NEW.usua_id_creador THEN
      RAISE EXCEPTION 'El creador debe coincidir con el usuario autenticado' USING ERRCODE = 'insufficient_privilege';
    END IF;
    SELECT r.rol_codigo INTO v_rol_creador FROM usuario u JOIN rol r USING (rol_id) WHERE u.usua_id = NEW.usua_id_creador;
    IF v_rol_creador IS DISTINCT FROM 'AGRONOMO_SUPERVISOR' THEN
      RAISE EXCEPTION 'Solo un Agrónomo/Supervisor crea planificaciones' USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF v_rol_dest IS NULL OR v_rol_dest NOT IN ('TECNICO', 'PRODUCTOR') THEN
      RAISE EXCEPTION 'El destinatario debe ser Técnico o Productor' USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF NEW.plan_estado <> 'pendiente' THEN
      RAISE EXCEPTION 'Toda planificación nace pendiente' USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF v_rol_dest = 'PRODUCTOR' THEN
      IF NEW.plan_id_origen IS NOT NULL THEN
        RAISE EXCEPTION 'La planificación dirigida al productor no sale de otra planificación' USING ERRCODE = 'integrity_constraint_violation';
      END IF;
    ELSE
      -- Actividad para un técnico: solo puede salir de una planificación que el productor ya aprobó
      IF NEW.plan_id_origen IS NULL THEN
        RAISE EXCEPTION 'Una actividad para un técnico debe salir de una planificación aprobada por el productor (plan_id_origen)' USING ERRCODE = 'integrity_constraint_violation';
      END IF;
      SELECT * INTO o FROM planificacion WHERE plan_id = NEW.plan_id_origen;
      IF NOT FOUND THEN
        RAISE EXCEPTION 'La planificación de origen % no existe', NEW.plan_id_origen USING ERRCODE = 'integrity_constraint_violation';
      END IF;
      SELECT r.rol_codigo INTO v_rol_origen FROM usuario u JOIN rol r USING (rol_id) WHERE u.usua_id = o.usua_id_destinatario;
      IF v_rol_origen IS DISTINCT FROM 'PRODUCTOR' THEN
        RAISE EXCEPTION 'La planificación de origen debe estar dirigida a un productor' USING ERRCODE = 'integrity_constraint_violation';
      END IF;
      IF o.plan_estado <> 'aceptada' THEN
        RAISE EXCEPTION 'La planificación de origen no está aprobada por el productor (estado: %)', o.plan_estado USING ERRCODE = 'integrity_constraint_violation';
      END IF;
      IF NEW.plan_fecha_inicio < o.plan_fecha_inicio
         OR (o.plan_fecha_fin IS NOT NULL AND COALESCE(NEW.plan_fecha_fin, NEW.plan_fecha_inicio) > o.plan_fecha_fin) THEN
        RAISE EXCEPTION 'Las fechas de la actividad deben estar dentro de las de la planificación aprobada (% a %)', o.plan_fecha_inicio, COALESCE(o.plan_fecha_fin::text, 'sin fin') USING ERRCODE = 'integrity_constraint_violation';
      END IF;
    END IF;
    RETURN NEW;
  END IF;
  -- UPDATE: la solicitud es inmutable; solo cambian las columnas de respuesta
  IF (to_jsonb(NEW) - ARRAY['plan_estado','plan_observacion_respuesta','plan_respondida_en','usua_id_respuesta'])
     <> (to_jsonb(OLD) - ARRAY['plan_estado','plan_observacion_respuesta','plan_respondida_en','usua_id_respuesta']) THEN
    RAISE EXCEPTION 'La solicitud de una planificación es inmutable' USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF NEW.plan_estado = OLD.plan_estado THEN
    IF (NEW.plan_observacion_respuesta, NEW.plan_respondida_en, NEW.usua_id_respuesta)
       IS DISTINCT FROM (OLD.plan_observacion_respuesta, OLD.plan_respondida_en, OLD.usua_id_respuesta) THEN
      RAISE EXCEPTION 'La respuesta de una planificación solo se fija al cambiar de estado' USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
  END IF;
  IF v_actor IS DISTINCT FROM OLD.usua_id_destinatario THEN
    RAISE EXCEPTION 'Solo el destinatario responde la planificación' USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF NOT ( (v_rol_dest = 'PRODUCTOR' AND ((OLD.plan_estado = 'pendiente' AND NEW.plan_estado IN ('aceptada', 'rechazada'))
                                       OR (OLD.plan_estado = 'aceptada'  AND NEW.plan_estado = 'completada')))
        OR (v_rol_dest = 'TECNICO'   AND OLD.plan_estado = 'pendiente' AND NEW.plan_estado = 'completada') ) THEN
    RAISE EXCEPTION 'Transición % -> % no permitida para el rol %', OLD.plan_estado, NEW.plan_estado, v_rol_dest USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF NEW.plan_estado = 'completada' THEN
    IF v_rol_dest = 'PRODUCTOR' AND EXISTS (SELECT 1 FROM planificacion h WHERE h.plan_id_origen = OLD.plan_id AND h.plan_estado = 'pendiente') THEN
      RAISE EXCEPTION 'La planificación aún tiene actividades de técnicos sin completar' USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF v_rol_dest = 'TECNICO' AND EXISTS (SELECT 1 FROM planificacion_lote l WHERE l.plan_id = OLD.plan_id AND l.plal_estado = 'pendiente') THEN
      RAISE EXCEPTION 'La actividad aún tiene lotes sin resultado: registre si se ejecutaron o no' USING ERRCODE = 'integrity_constraint_violation';
    END IF;
  END IF;
  NEW.plan_respondida_en := COALESCE(NEW.plan_respondida_en, now());
  NEW.usua_id_respuesta := v_actor;
  RETURN NEW;
END $$;
COMMENT ON FUNCTION sigat.fn_planificacion_valida() IS
  'SIGAT v8 candidata: refuerza identidad real del creador; mantiene aprobación productor -> asignación técnico; requiere sesión autenticada sigat.usuario_actual.';

CREATE OR REPLACE FUNCTION fn_planificacion_lote_resultado() RETURNS trigger LANGUAGE plpgsql SET search_path = sigat, public AS $$
DECLARE v_estado text; v_dest integer; v_rol text; v_vis_usua integer; v_actor integer := fn_usuario_actual(); v_oper operacion_sync%ROWTYPE;
BEGIN
  IF (to_jsonb(NEW) - ARRAY['plal_estado','plal_observacion','plal_resuelta_en','visi_id','plal_oper_id'])
     <> (to_jsonb(OLD) - ARRAY['plal_estado','plal_observacion','plal_resuelta_en','visi_id','plal_oper_id']) THEN
    RAISE EXCEPTION 'Solo cambia el resultado del lote; la planificación y el lote no se modifican' USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF (NEW.plal_estado, NEW.plal_observacion, NEW.plal_resuelta_en, NEW.visi_id)
     IS NOT DISTINCT FROM (OLD.plal_estado, OLD.plal_observacion, OLD.plal_resuelta_en, OLD.visi_id) THEN
    RETURN NEW;
  END IF;
  SELECT p.plan_estado, p.usua_id_destinatario, r.rol_codigo INTO v_estado, v_dest, v_rol
    FROM planificacion p JOIN usuario u ON u.usua_id = p.usua_id_destinatario JOIN rol r ON r.rol_id = u.rol_id WHERE p.plan_id = NEW.plan_id;
  IF v_rol <> 'TECNICO' THEN
    RAISE EXCEPTION 'Solo las actividades asignadas a un técnico registran resultado por lote' USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF v_estado <> 'pendiente' THEN
    RAISE EXCEPTION 'La actividad ya está completada: sus resultados no se modifican' USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF v_actor IS DISTINCT FROM v_dest THEN
    RAISE EXCEPTION 'Solo el técnico asignado registra el resultado de la actividad' USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF OLD.plal_estado = 'pendiente' THEN
    IF NEW.plal_estado <> 'pendiente' THEN NEW.plal_resuelta_en := COALESCE(NEW.plal_resuelta_en, now()); END IF;
  ELSIF (NEW.plal_estado, NEW.plal_observacion, NEW.plal_resuelta_en) IS DISTINCT FROM (OLD.plal_estado, OLD.plal_observacion, OLD.plal_resuelta_en)
        OR OLD.visi_id IS NOT NULL THEN
    RAISE EXCEPTION 'El resultado ya registrado no se modifica (solo puede enlazarse la visita que lo respalda)' USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  -- El enlace a una operación offline no puede sustituirse ni añadirse después de registrar el resultado.
  IF OLD.plal_oper_id IS NOT NULL AND NEW.plal_oper_id IS DISTINCT FROM OLD.plal_oper_id THEN
    RAISE EXCEPTION 'La operación de sincronización del resultado es inmutable' USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF NEW.plal_oper_id IS NOT NULL AND NEW.plal_oper_id IS DISTINCT FROM OLD.plal_oper_id THEN
    IF OLD.plal_estado <> 'pendiente' OR NEW.plal_estado = 'pendiente' THEN
      RAISE EXCEPTION 'La operación offline se vincula solo al registrar inicialmente el resultado' USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    SELECT * INTO v_oper FROM operacion_sync WHERE oper_id = NEW.plal_oper_id;
    IF NOT FOUND OR v_oper.oper_entidad IS DISTINCT FROM 'planificacion_lote'
       OR v_oper.oper_registro_id IS DISTINCT FROM NEW.plal_sync_id
       OR v_oper.usua_id IS DISTINCT FROM v_dest THEN
      RAISE EXCEPTION 'Operación offline no coincide con la actividad, el usuario o la entidad' USING ERRCODE = 'integrity_constraint_violation';
    END IF;
  END IF;
  IF NEW.visi_id IS NOT NULL AND NEW.visi_id IS DISTINCT FROM OLD.visi_id THEN
    SELECT usua_id INTO v_vis_usua FROM visita WHERE visi_id = NEW.visi_id;
    IF v_vis_usua IS DISTINCT FROM v_dest THEN
      RAISE EXCEPTION 'La visita que respalda el resultado debe ser del técnico asignado' USING ERRCODE = 'integrity_constraint_violation';
    END IF;
  END IF;
  RETURN NEW;
END $$;
COMMENT ON FUNCTION sigat.fn_planificacion_lote_resultado() IS
  'SIGAT v8 candidata: registro de resultado por técnico y validación del enlace opcional a operacion_sync de la misma actividad y usuario.';

-- P4. Aviso al agrónomo tras respuesta del productor.
CREATE OR REPLACE FUNCTION sigat.fn_planificacion_respuesta_notifica() RETURNS trigger
LANGUAGE plpgsql SET search_path = sigat, public AS $$
DECLARE v_cate integer; v_evento text; v_titulo text; v_cuerpo text;
BEGIN
  IF NEW.plan_estado IS NOT DISTINCT FROM OLD.plan_estado THEN RETURN NULL; END IF;
  IF OLD.plan_estado <> 'pendiente' OR NEW.plan_estado NOT IN ('aceptada','rechazada') THEN RETURN NULL; END IF;
  -- Se avisa al creador de la respuesta del productor; no envía actividad a técnico antes de aprobar.
  IF NOT EXISTS (
    SELECT 1 FROM usuario u JOIN rol r USING (rol_id)
    WHERE u.usua_id = NEW.usua_id_destinatario AND r.rol_codigo = 'PRODUCTOR'
  ) THEN RETURN NULL; END IF;
  SELECT cate_id INTO v_cate FROM categoria_notificacion WHERE cate_codigo = 'asignacion';
  IF v_cate IS NULL THEN RETURN NULL; END IF;
  v_evento := 'plan:' || NEW.plan_id::text || ':respuesta';
  v_titulo := CASE WHEN NEW.plan_estado = 'aceptada' THEN 'Planificación aprobada'
                   ELSE 'Planificación rechazada' END;
  v_cuerpo := 'El productor ' || CASE WHEN NEW.plan_estado = 'aceptada' THEN 'aprobó' ELSE 'rechazó' END
      || ' la planificación «' || NEW.plan_actividad || '».'
      || CASE WHEN NEW.plan_observacion_respuesta IS NOT NULL
              THEN ' Observación: ' || NEW.plan_observacion_respuesta ELSE '' END;
  INSERT INTO notificacion
    (usua_id, cate_id, noti_titulo, noti_cuerpo, noti_evento_clave, noti_destino_ruta, noti_destino_argumento)
  VALUES (NEW.usua_id_creador, v_cate, v_titulo, v_cuerpo, v_evento,
          '/plannings/detail', NEW.plan_id::text)
  ON CONFLICT (usua_id, noti_evento_clave) DO NOTHING;
  RETURN NULL;
END $$;
COMMENT ON FUNCTION sigat.fn_planificacion_respuesta_notifica() IS
  'SIGAT v8 candidata: notifica al agrónomo la aprobación/rechazo del productor; idempotente por clave de evento.';
DROP TRIGGER IF EXISTS trg_planificacion_respuesta_notifica ON sigat.planificacion;
CREATE TRIGGER trg_planificacion_respuesta_notifica
AFTER UPDATE OF plan_estado ON sigat.planificacion
FOR EACH ROW WHEN (OLD.plan_estado IS DISTINCT FROM NEW.plan_estado)
EXECUTE FUNCTION sigat.fn_planificacion_respuesta_notifica();

COMMENT ON SCHEMA sigat IS
  'SIGAT v8 candidata - ajustes de validación, offline y notificaciones sobre la arquitectura v7 (provisional pendiente de pruebas de integración).';
COMMIT;
