-- =====================================================================
-- SIGAT v7 - FUNCIONES Y REGLAS AUTOMÁTICAS (26 funciones, 16 de ellas disparadores de validación)
-- Se suman a las 8 funciones base de 01_esquema_completo.sql (fn_usuario_actual, fn_auditar,
-- fn_bloquear_*, fn_registro_version_valida, fn_marcar_sincronizacion, fn_visita_integridad, fn_trampa_valida).
-- Necesita: 01, 02 y 03. Se puede volver a ejecutar.
-- El actor de la sesión se fija con:  SET LOCAL sigat.usuario_actual = '<usua_id>';
-- =====================================================================
SET search_path = sigat, public;

-- ---------------------------------------------------------------------
-- A. CONSULTAS: quién ve qué
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_lotes_visibles(p_usua integer DEFAULT fn_usuario_actual())
RETURNS TABLE (lote_id integer) LANGUAGE sql STABLE SET search_path = sigat, public AS $$
  SELECT l.lote_id FROM lote l
   WHERE EXISTS (SELECT 1 FROM usuario u JOIN rol r USING (rol_id) WHERE u.usua_id = p_usua AND r.rol_codigo = 'ADMINISTRADOR')
  UNION
  SELECT l.lote_id FROM lote l
   JOIN v_acceso_predio a ON a.pred_id = l.pred_id AND a.usua_id = p_usua
   JOIN usuario u ON u.usua_id = p_usua JOIN rol r ON r.rol_id = u.rol_id
   WHERE r.rol_codigo IN ('PRODUCTOR', 'AGRONOMO_SUPERVISOR')
  UNION
  SELECT a.lote_id FROM v_asignacion_lote_tecnico a
   WHERE a.usua_id = p_usua AND a.vigente
$$;
COMMENT ON FUNCTION fn_lotes_visibles(integer) IS 'Lotes que un usuario puede ver: Administrador todos; Productor y Agrónomo/Supervisor los de sus predios; Técnico solo los lotes de sus asignaciones vigentes, sin necesidad de aceptar nada (p. ej. Usuario A: lotes A y C; Usuario B: lotes B y D; ninguno ve los del otro). Las funciones fn_*_app la usan para filtrar lo que recibe el teléfono.';

CREATE OR REPLACE FUNCTION fn_actividad_lote(p_usua integer DEFAULT fn_usuario_actual())
RETURNS SETOF v_actividad_lote LANGUAGE sql STABLE SET search_path = sigat, public AS $$
  SELECT v.* FROM v_actividad_lote v WHERE v.lote_id IN (SELECT lote_id FROM fn_lotes_visibles(p_usua)) $$;
COMMENT ON FUNCTION fn_actividad_lote(integer) IS 'v_actividad_lote filtrada a los lotes que el usuario puede ver.';

CREATE OR REPLACE FUNCTION fn_actividad_tecnico(p_usua integer DEFAULT fn_usuario_actual())
RETURNS SETOF v_actividad_tecnico LANGUAGE sql STABLE SET search_path = sigat, public AS $$
  SELECT v.* FROM v_actividad_tecnico v
   WHERE CASE WHEN EXISTS (SELECT 1 FROM usuario u JOIN rol r USING (rol_id) WHERE u.usua_id = p_usua AND r.rol_codigo = 'TECNICO')
              THEN v.usua_id = p_usua
              ELSE v.lote_id IN (SELECT lote_id FROM fn_lotes_visibles(p_usua)) END $$;
COMMENT ON FUNCTION fn_actividad_tecnico(integer) IS 'v_actividad_tecnico filtrada: el técnico ve solo sus propias actividades; los demás roles, las de los lotes que pueden ver.';

CREATE OR REPLACE FUNCTION fn_lote_app(p_usua integer DEFAULT fn_usuario_actual())
RETURNS SETOF v_lote_app LANGUAGE sql STABLE SET search_path = sigat, public AS $$
  SELECT v.* FROM v_lote_app v WHERE v.lote_id IN (SELECT lote_id FROM fn_lotes_visibles(p_usua)) $$;
COMMENT ON FUNCTION fn_lote_app(integer) IS 'v_lote_app filtrada a los lotes que el usuario puede ver (lista de lotes del teléfono).';

CREATE OR REPLACE FUNCTION fn_lote_resumen_app(p_usua integer DEFAULT fn_usuario_actual())
RETURNS SETOF v_lote_resumen_app LANGUAGE sql STABLE SET search_path = sigat, public AS $$
  SELECT v.* FROM v_lote_resumen_app v WHERE v.lote_id IN (SELECT lote_id FROM fn_lotes_visibles(p_usua)) $$;
COMMENT ON FUNCTION fn_lote_resumen_app(integer) IS 'v_lote_resumen_app filtrada a los lotes que el usuario puede ver.';

CREATE OR REPLACE FUNCTION fn_mtd_serie_lote(p_usua integer DEFAULT fn_usuario_actual())
RETURNS SETOF v_mtd_serie_lote LANGUAGE sql STABLE SET search_path = sigat, public AS $$
  SELECT v.* FROM v_mtd_serie_lote v WHERE v.lote_id IN (SELECT lote_id FROM fn_lotes_visibles(p_usua)) $$;
COMMENT ON FUNCTION fn_mtd_serie_lote(integer) IS 'v_mtd_serie_lote filtrada a los lotes que el usuario puede ver.';

CREATE OR REPLACE FUNCTION fn_trampa_app(p_usua integer DEFAULT fn_usuario_actual())
RETURNS SETOF v_trampa_app LANGUAGE sql STABLE SET search_path = sigat, public AS $$
  SELECT v.* FROM v_trampa_app v WHERE v.lote_id IN (SELECT lote_id FROM fn_lotes_visibles(p_usua)) $$;
COMMENT ON FUNCTION fn_trampa_app(integer) IS 'v_trampa_app filtrada a las trampas de los lotes que el usuario puede ver.';

-- ---------------------------------------------------------------------
-- B. CÁLCULOS
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_etapa_derivada(p_lote integer, p_fecha date)
RETURNS integer LANGUAGE sql STABLE SET search_path = sigat, public AS $$
  SELECT r.feno_id
    FROM lote l
    JOIN fenologia_regla r ON r.espc_id = l.espc_id
     AND r.fenr_vigente_desde <= p_fecha AND (r.fenr_vigente_hasta IS NULL OR r.fenr_vigente_hasta > p_fecha)
     AND (p_fecha - l.lote_fecha_plantacion) BETWEEN r.fenr_dias_desde AND r.fenr_dias_hasta
   WHERE l.lote_id = p_lote AND l.lote_fecha_plantacion IS NOT NULL
   ORDER BY r.fenr_vigente_desde DESC LIMIT 1
$$;
COMMENT ON FUNCTION fn_etapa_derivada(integer, date) IS 'RN-012: etapa fenológica derivada del lote en una fecha, según la tabla de reglas vigente en esa fecha. Nulo si falta la fecha de plantación o la regla.';

CREATE OR REPLACE FUNCTION fn_lote_que_contiene(p_punto geometry, p_instante timestamptz DEFAULT now())
RETURNS SETOF integer LANGUAGE sql STABLE SET search_path = sigat, public AS $$
  SELECT g.lote_id FROM lote_geometria g
   WHERE g.lotg_vigente_desde <= p_instante AND (g.lotg_vigente_hasta IS NULL OR g.lotg_vigente_hasta > p_instante)
     AND ST_Covers(g.lotg_geom, p_punto)
$$;
COMMENT ON FUNCTION fn_lote_que_contiene(geometry, timestamptz) IS 'Devuelve el/los lotes cuya geometría vigente en p_instante cubre el punto (usa el índice GiST de lote_geometria).';

CREATE OR REPLACE FUNCTION fn_mtd_lectura_valida(p_peri bigint)
RETURNS TABLE (lect_id uuid, tram_id integer, lect_especimenes integer) LANGUAGE sql STABLE SET search_path = sigat, public AS $$
  SELECT l.lect_id, l.tram_id, l.lect_especimenes
    FROM periodo_trampeo p
    JOIN v_lectura_vigente l ON l.lect_linaje = 'inspeccion_oficial' AND l.lect_leida
    JOIN ubicacion_trampa u ON u.ubic_id = l.ubic_id AND u.lote_id = p.lote_id
   WHERE p.peri_id = p_peri
     AND l.lect_t_observacion::date BETWEEN p.peri_inicio AND p.peri_fin
$$;
COMMENT ON FUNCTION fn_mtd_lectura_valida(bigint) IS 'Lecturas que alimentan el MTD de un periodo: solo inspección oficial, leídas, no anuladas, con trampa asignada al lote y dentro del periodo (RN-013 / RN-014).';

-- ---------------------------------------------------------------------
-- C. TRIGGERS DE VALIDACIÓN
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_archivo_adjunto_valida() RETURNS trigger LANGUAGE plpgsql SET search_path = sigat, public AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    NEW.arch_t_sincronizacion := now();
    RETURN NEW;
  END IF;
  IF (to_jsonb(NEW) - ARRAY['arch_estado','arch_motivo_rechazo','arch_ref_almacenamiento','arch_t_almacenado','arch_paginas'])
     <> (to_jsonb(OLD) - ARRAY['arch_estado','arch_motivo_rechazo','arch_ref_almacenamiento','arch_t_almacenado','arch_paginas']) THEN
    RAISE EXCEPTION 'La identidad de un archivo adjunto no se modifica' USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF NEW.arch_estado <> OLD.arch_estado AND OLD.arch_estado <> 'pendiente_contenido' THEN
    RAISE EXCEPTION 'El estado del archivo solo avanza desde pendiente_contenido (actual: %)', OLD.arch_estado USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  RETURN NEW;
END $$;
COMMENT ON FUNCTION fn_archivo_adjunto_valida() IS 'Trigger de archivo: identidad inmutable, estado solo avanza desde pendiente_contenido y reloj del servidor para t_sincronizacion.';

CREATE OR REPLACE FUNCTION fn_concepto_valida() RETURNS trigger LANGUAGE plpgsql SET search_path = sigat, public AS $$
DECLARE c text;
BEGIN
  SELECT indi_resultado_contraste INTO c FROM indice_mtd WHERE indi_id = NEW.indi_id;
  IF NEW.conc_resultado = 'no_emitido' AND c IS DISTINCT FROM 'sin_umbral' THEN
    RAISE EXCEPTION 'Concepto no_emitido solo cuando el MTD no tiene umbral configurado (contraste actual: %)', c USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF NEW.conc_resultado <> 'no_emitido' AND c = 'sin_umbral' THEN
    RAISE EXCEPTION 'No se puede emitir apto/no_apto sin umbral configurado (UQQ-004)' USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF NEW.conc_resultado = 'apto' AND c <> 'por_debajo_umbral' THEN
    RAISE EXCEPTION 'Apto exige MTD por debajo del umbral (contraste: %)', c USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF NEW.conc_resultado = 'no_apto' AND c <> 'igual_o_superior_umbral' THEN
    RAISE EXCEPTION 'No apto exige MTD igual o superior al umbral (contraste: %)', c USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  RETURN NEW;
END $$;
COMMENT ON FUNCTION fn_concepto_valida() IS 'Concepto de aptitud: solo es «no_emitido» cuando el MTD no tiene umbral configurado (RF-024); apto/no_apto deben coincidir con el contraste del MTD.';

CREATE OR REPLACE FUNCTION fn_hallazgo_valida() RETURNS trigger LANGUAGE plpgsql SET search_path = sigat, public AS $$
BEGIN
  IF NEW.retc_id IS NOT NULL AND NOT EXISTS (
       SELECT 1 FROM reticula_celda c JOIN reticula r USING (reti_id) JOIN lote l ON l.pred_id = r.pred_id
        WHERE c.retc_id = NEW.retc_id AND l.lote_id = NEW.lote_id) THEN
    RAISE EXCEPTION 'La celda % no pertenece a una retícula del predio del lote %', NEW.retc_id, NEW.lote_id USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  RETURN NEW;
END $$;
COMMENT ON FUNCTION fn_hallazgo_valida() IS 'RF-010: la celda del hallazgo debe pertenecer a una retícula del predio del lote.';

CREATE OR REPLACE FUNCTION fn_lectura_valida() RETURNS trigger LANGUAGE plpgsql SET search_path = sigat, public AS $$
DECLARE v_pred integer; v_dia date; v_tram0 integer; u record; v_cod text;
BEGIN
  SELECT tram_codigo INTO v_cod FROM trampa WHERE tram_id = NEW.tram_id;
  IF v_cod IS NULL THEN
    RAISE EXCEPTION 'La trampa % no tiene código ICA: no se puede registrar lectura', NEW.tram_id USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  SELECT v.pred_id, (v.visi_t_inicio_obs AT TIME ZONE p.pred_zona_horaria)::date INTO v_pred, v_dia
    FROM visita v JOIN predio p ON p.pred_id = v.pred_id WHERE v.visi_id = NEW.visi_id;
  SELECT * INTO u FROM ubicacion_trampa WHERE ubic_id = NEW.ubic_id;
  IF u.tram_id <> NEW.tram_id THEN
    RAISE EXCEPTION 'La ubicación % no es de la trampa %', NEW.ubic_id, NEW.tram_id USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF u.pred_id <> v_pred THEN
    RAISE EXCEPTION 'La ubicación no es del predio de la visita' USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF v_dia < u.ubic_fecha OR (u.ubic_fecha_fin IS NOT NULL AND v_dia >= u.ubic_fecha_fin) THEN
    RAISE EXCEPTION 'La ubicación no estaba vigente el día observado (%)', v_dia USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF NEW.lect_version > 1 THEN
    SELECT tram_id INTO v_tram0 FROM lectura_trampa WHERE lect_registro_id = NEW.lect_registro_id AND lect_version = 1;
    IF v_tram0 <> NEW.tram_id THEN
      RAISE EXCEPTION 'Una corrección no puede cambiar la trampa de la lectura' USING ERRCODE = 'integrity_constraint_violation';
    END IF;
  END IF;
  RETURN NEW;
END $$;
COMMENT ON FUNCTION fn_lectura_valida() IS 'Lectura de trampa: la trampa debe tener código ICA, la ubicación debe ser del predio de la visita y vigente en la fecha observada, y una corrección no puede cambiar la trampa.';

CREATE OR REPLACE FUNCTION fn_lote_geometria_valida() RETURNS trigger LANGUAGE plpgsql SET search_path = sigat, public AS $$
DECLARE g geometry;
BEGIN
  SELECT p.pred_geom INTO g FROM lote l JOIN predio p USING (pred_id) WHERE l.lote_id = NEW.lote_id;
  IF g IS NOT NULL AND NOT ST_Covers(g, NEW.lotg_geom) THEN
    RAISE EXCEPTION 'La geometría del lote % queda fuera del límite del predio (RF-084)', NEW.lote_id USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  RETURN NEW;
END $$;
COMMENT ON FUNCTION fn_lote_geometria_valida() IS 'RF-084: la geometría de un lote debe quedar contenida en el límite del predio (si el límite ya está cargado).';

CREATE OR REPLACE FUNCTION fn_notificacion_valida() RETURNS trigger LANGUAGE plpgsql SET search_path = sigat, public AS $$
BEGIN
  IF (to_jsonb(NEW) - 'noti_leida_en') <> (to_jsonb(OLD) - 'noti_leida_en') THEN
    RAISE EXCEPTION 'El contenido de una notificación no se modifica' USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF OLD.noti_leida_en IS NOT NULL AND NEW.noti_leida_en IS DISTINCT FROM OLD.noti_leida_en THEN
    RAISE EXCEPTION 'La notificación ya fue leída' USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  RETURN NEW;
END $$;
COMMENT ON FUNCTION fn_notificacion_valida() IS 'Trigger de notificacion: contenido inmutable; solo se marca leída, una vez.';

CREATE OR REPLACE FUNCTION fn_periodo_valida() RETURNS trigger LANGUAGE plpgsql SET search_path = sigat, public AS $$
BEGIN
  IF NOT EXISTS (
       SELECT 1 FROM programa_inspeccion g JOIN lote l ON l.pred_id = g.pred_id
        WHERE g.prog_id = NEW.prog_id AND l.lote_id = NEW.lote_id
          AND g.prog_vigente_desde <= NEW.peri_fin
          AND (g.prog_vigente_hasta IS NULL OR g.prog_vigente_hasta > NEW.peri_fin)) THEN
    RAISE EXCEPTION 'El programa % no es del predio del lote o no está vigente al cierre del periodo (RN-003)', NEW.prog_id USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  RETURN NEW;
END $$;
COMMENT ON FUNCTION fn_periodo_valida() IS 'Periodo de trampeo: el programa debe ser del predio del lote y estar vigente en la fecha final del periodo (RN-003).';

CREATE OR REPLACE FUNCTION fn_planificacion_valida() RETURNS trigger LANGUAGE plpgsql SET search_path = sigat, public AS $$
DECLARE v_rol_creador text; v_rol_dest text; v_rol_origen text; v_actor integer := fn_usuario_actual(); o planificacion%ROWTYPE;
BEGIN
  SELECT r.rol_codigo INTO v_rol_dest FROM usuario u JOIN rol r USING (rol_id) WHERE u.usua_id = NEW.usua_id_destinatario;
  IF TG_OP = 'INSERT' THEN
    SELECT r.rol_codigo INTO v_rol_creador FROM usuario u JOIN rol r USING (rol_id) WHERE u.usua_id = NEW.usua_id_creador;
    IF v_rol_creador <> 'AGRONOMO_SUPERVISOR' THEN
      RAISE EXCEPTION 'Solo un Agrónomo/Supervisor crea planificaciones' USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF v_rol_dest NOT IN ('TECNICO', 'PRODUCTOR') THEN
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
COMMENT ON FUNCTION fn_planificacion_valida() IS 'Trigger de planificacion. Crea solo un Agrónomo/Supervisor; el destinatario es Productor (planificación a aprobar) o Técnico (actividad asignada). Una actividad de técnico exige plan_id_origen: una planificación de un productor ya aprobada (aceptada), con fechas dentro de las aprobadas. Transiciones del Productor: pendiente→aceptada|rechazada y aceptada→completada (solo sin actividades de técnicos pendientes); del Técnico: pendiente→completada (solo con todos sus lotes resueltos). Solo el destinatario responde; la base registra quién (usua_id_respuesta) y cuándo; la solicitud es inmutable.';

CREATE OR REPLACE FUNCTION fn_planificacion_lote_valida() RETURNS trigger LANGUAGE plpgsql SET search_path = sigat, public AS $$
DECLARE v_estado text; v_dest integer; v_plan uuid; v_origen uuid;
BEGIN
  v_plan := CASE WHEN TG_OP = 'DELETE' THEN OLD.plan_id ELSE NEW.plan_id END;
  SELECT plan_estado, usua_id_destinatario, plan_id_origen INTO v_estado, v_dest, v_origen FROM planificacion WHERE plan_id = v_plan;
  IF v_estado <> 'pendiente' THEN
    RAISE EXCEPTION 'Los lotes de una planificación no pendiente (%) están congelados', v_estado USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF TG_OP = 'DELETE' THEN
    IF OLD.plal_estado <> 'pendiente' THEN
      RAISE EXCEPTION 'No se puede quitar el lote %: ya tiene resultado (%)', OLD.lote_id, OLD.plal_estado USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN OLD;
  END IF;
  IF NEW.plal_estado <> 'pendiente' THEN
    RAISE EXCEPTION 'Un lote entra a la planificación sin resultado (pendiente)' USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM lote l JOIN v_acceso_predio a ON a.pred_id = l.pred_id AND a.usua_id = v_dest WHERE l.lote_id = NEW.lote_id) THEN
    RAISE EXCEPTION 'El destinatario no tiene acceso al predio del lote %', NEW.lote_id USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF v_origen IS NOT NULL AND NOT EXISTS (SELECT 1 FROM planificacion_lote o WHERE o.plan_id = v_origen AND o.lote_id = NEW.lote_id) THEN
    RAISE EXCEPTION 'El lote % no está en la planificación que aprobó el productor', NEW.lote_id USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  RETURN NEW;
END $$;
COMMENT ON FUNCTION fn_planificacion_lote_valida() IS 'Trigger de planificacion_lote (alta y baja): congela los lotes cuando la planificación deja de estar pendiente; no deja quitar un lote que ya tiene resultado; exige que cada lote sea de un predio al que el destinatario tiene acceso (v_acceso_predio) y, en una actividad de técnico, que el lote esté en la planificación aprobada por el productor.';

CREATE OR REPLACE FUNCTION fn_planificacion_lote_resultado() RETURNS trigger LANGUAGE plpgsql SET search_path = sigat, public AS $$
DECLARE v_estado text; v_dest integer; v_rol text; v_vis_usua integer; v_actor integer := fn_usuario_actual();
BEGIN
  IF (to_jsonb(NEW) - ARRAY['plal_estado','plal_observacion','plal_resuelta_en','visi_id'])
     <> (to_jsonb(OLD) - ARRAY['plal_estado','plal_observacion','plal_resuelta_en','visi_id']) THEN
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
  IF NEW.visi_id IS NOT NULL AND NEW.visi_id IS DISTINCT FROM OLD.visi_id THEN
    SELECT usua_id INTO v_vis_usua FROM visita WHERE visi_id = NEW.visi_id;
    IF v_vis_usua IS DISTINCT FROM v_dest THEN
      RAISE EXCEPTION 'La visita que respalda el resultado debe ser del técnico asignado' USING ERRCODE = 'integrity_constraint_violation';
    END IF;
  END IF;
  RETURN NEW;
END $$;
COMMENT ON FUNCTION fn_planificacion_lote_resultado() IS 'Trigger de planificacion_lote (cambios): registra el resultado de una actividad en un lote (pendiente → ejecutada | no_ejecutada). Solo el técnico asignado, solo mientras la actividad está pendiente, y una sola vez; la justificación de no ejecutada la exige la regla CHECK. Después solo puede enlazarse la visita que respalda la ejecución (debe ser del mismo técnico).';

CREATE OR REPLACE FUNCTION fn_planificacion_notifica() RETURNS trigger LANGUAGE plpgsql SET search_path = sigat, public AS $$
DECLARE v_rol text; v_cate integer; v_creador text; v_titulo text; v_cuerpo text; v_clave text;
BEGIN
  SELECT r.rol_codigo INTO v_rol FROM usuario u JOIN rol r USING (rol_id) WHERE u.usua_id = NEW.usua_id_destinatario;
  SELECT pe.pers_nombre || ' ' || pe.pers_apellido INTO v_creador FROM usuario u JOIN persona pe ON pe.pers_cc = u.pers_cc WHERE u.usua_id = NEW.usua_id_creador;
  SELECT cate_id INTO v_cate FROM categoria_notificacion WHERE cate_codigo = 'asignacion';
  IF v_cate IS NULL THEN RETURN NULL; END IF;   -- sin la categoría no se bloquea la planificación
  IF v_rol = 'PRODUCTOR' THEN
    v_titulo := 'Planificación por aprobar';
    v_clave  := 'plan:' || NEW.plan_id || ':solicitud';
    v_cuerpo := v_creador || ' propone «' || NEW.plan_actividad || '» desde el ' || to_char(NEW.plan_fecha_inicio, 'DD/MM/YYYY')
                || COALESCE(' hasta el ' || to_char(NEW.plan_fecha_fin, 'DD/MM/YYYY'), '') || '. Apruébala o recházala con tus observaciones.';
  ELSIF v_rol = 'TECNICO' THEN
    v_titulo := 'Nueva actividad asignada';
    v_clave  := 'plan:' || NEW.plan_id || ':asignacion';
    v_cuerpo := v_creador || ' te asignó «' || NEW.plan_actividad || '» desde el ' || to_char(NEW.plan_fecha_inicio, 'DD/MM/YYYY')
                || COALESCE(' hasta el ' || to_char(NEW.plan_fecha_fin, 'DD/MM/YYYY'), '') || '. Revisa los lotes asignados.';
  ELSE
    RETURN NULL;
  END IF;
  INSERT INTO notificacion (usua_id, cate_id, noti_titulo, noti_cuerpo, noti_evento_clave, noti_destino_ruta, noti_destino_argumento)
  VALUES (NEW.usua_id_destinatario, v_cate, v_titulo, v_cuerpo, v_clave, '/plannings/detail', NEW.plan_id::text)
  ON CONFLICT (usua_id, noti_evento_clave) DO NOTHING;
  RETURN NULL;
END $$;
COMMENT ON FUNCTION fn_planificacion_notifica() IS 'Trigger AFTER INSERT de planificacion: crea el aviso (categoría asignacion) para el destinatario. Si es un productor: solicitud de aprobación; si es un técnico: actividad ya autorizada (solo puede existir tras la aprobación). La clave del evento (plan:<id>:solicitud | :asignacion) evita avisos repetidos.';

CREATE OR REPLACE FUNCTION fn_dispositivo_sync() RETURNS trigger LANGUAGE plpgsql SET search_path = sigat, public AS $$
DECLARE v_disp uuid; v_activo boolean;
BEGIN
  IF TG_TABLE_NAME = 'operacion_sync' THEN v_disp := NEW.disp_id;
  ELSE SELECT disp_id INTO v_disp FROM operacion_sync WHERE oper_id = NEW.oper_id; END IF;
  IF TG_OP = 'INSERT' AND TG_WHEN = 'BEFORE' THEN
    SELECT disp_activo INTO v_activo FROM dispositivo WHERE disp_id = v_disp;
    IF v_activo IS NOT TRUE THEN
      RAISE EXCEPTION 'El dispositivo % está dado de baja o no existe: no se reciben operaciones nuevas', v_disp USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
  END IF;
  UPDATE dispositivo SET disp_ultima_sync = now() WHERE disp_id = v_disp;
  RETURN NULL;
END $$;
COMMENT ON FUNCTION fn_dispositivo_sync() IS 'Trigger de operacion_sync (antes de insertar: rechaza operaciones de un dispositivo dado de baja) y de operacion_sync / recepcion_sync (después de insertar: actualiza disp_ultima_sync).';

CREATE OR REPLACE FUNCTION fn_programa_valida() RETURNS trigger LANGUAGE plpgsql SET search_path = sigat, public AS $$
DECLARE r reticula;
BEGIN
  SELECT * INTO r FROM reticula WHERE reti_id = NEW.reti_id;
  IF r.pred_id <> NEW.pred_id THEN
    RAISE EXCEPTION 'La retícula % no es del predio del programa', NEW.reti_id USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF r.reti_resolucion_m % NEW.prog_distancia_min_trampas_m <> 0 THEN
    RAISE EXCEPTION 'La resolución de la retícula (% m) debe ser múltiplo de la distancia mínima entre trampas (% m) (RI-002/RN-004)',
      r.reti_resolucion_m, NEW.prog_distancia_min_trampas_m USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  RETURN NEW;
END $$;
COMMENT ON FUNCTION fn_programa_valida() IS 'Programa de inspección: la retícula debe ser del mismo predio y su resolución múltiplo de la distancia mínima entre trampas (RI-002 / RN-004).';

CREATE OR REPLACE FUNCTION fn_reticula_inmutable() RETURNS trigger LANGUAGE plpgsql SET search_path = sigat, public AS $$
BEGIN
  IF NEW.pred_id <> OLD.pred_id OR NEW.reti_resolucion_m <> OLD.reti_resolucion_m THEN
    RAISE EXCEPTION 'La resolución y el predio de una retícula no se modifican; cree otra retícula' USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  RETURN NEW;
END $$;
COMMENT ON FUNCTION fn_reticula_inmutable() IS 'La resolución y el predio de una retícula no se modifican; se crea otra retícula.';

CREATE OR REPLACE FUNCTION fn_ubicacion_trampa_valida() RETURNS trigger LANGUAGE plpgsql SET search_path = sigat, public AS $$
DECLARE v_cod text; rg rango_departamento; v_retpred integer; v_lotepred integer;
BEGIN
  IF NEW.ubic_origen = 'legado' THEN RETURN NEW; END IF;
  SELECT tram_codigo INTO v_cod FROM trampa WHERE tram_id = NEW.tram_id;
  IF v_cod IS NULL THEN
    RAISE EXCEPTION 'La trampa % no tiene código ICA: no se puede ubicar', NEW.tram_id USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  SELECT g.* INTO rg FROM predio p JOIN municipio m USING (muni_id) JOIN rango_departamento g ON g.depa_id = m.depa_id WHERE p.pred_id = NEW.pred_id;
  IF FOUND AND NOT (NEW.ubic_long BETWEEN rg.rang_long_min AND rg.rang_long_max AND NEW.ubic_lat BETWEEN rg.rang_lat_min AND rg.rang_lat_max) THEN
    RAISE EXCEPTION 'Coordenadas (%, %) fuera del rango del departamento del predio (RN-006)', NEW.ubic_long, NEW.ubic_lat USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  IF NEW.retc_id IS NOT NULL THEN
    SELECT r.pred_id INTO v_retpred FROM reticula_celda c JOIN reticula r USING (reti_id) WHERE c.retc_id = NEW.retc_id;
    IF v_retpred IS DISTINCT FROM NEW.pred_id THEN
      RAISE EXCEPTION 'La celda % no es de una retícula del predio %', NEW.retc_id, NEW.pred_id USING ERRCODE = 'integrity_constraint_violation';
    END IF;
  END IF;
  SELECT pred_id INTO v_lotepred FROM lote WHERE lote_id = NEW.lote_id;
  IF v_lotepred IS DISTINCT FROM NEW.pred_id THEN
    RAISE EXCEPTION 'El lote % no pertenece al predio %', NEW.lote_id, NEW.pred_id USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  RETURN NEW;
END $$;
COMMENT ON FUNCTION fn_ubicacion_trampa_valida() IS 'Ubicación de trampa: exige código ICA, coordenadas dentro del rango del departamento del predio (RN-006 / RF-084), celda de retícula del mismo predio y lote del mismo predio.';

CREATE OR REPLACE FUNCTION fn_usuario_predio_valida() RETURNS trigger LANGUAGE plpgsql SET search_path = sigat, public AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM usuario u JOIN rol r USING (rol_id) WHERE u.usua_id = NEW.usua_id AND r.rol_ambito = 'global') THEN
    RAISE EXCEPTION 'Un usuario con rol de ámbito global no se asigna a un predio' USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  RETURN NEW;
END $$;
COMMENT ON FUNCTION fn_usuario_predio_valida() IS 'Un usuario cuyo rol es de ámbito global no puede asignarse a un predio.';

-- ---------------------------------------------------------------------
-- D. ACTIVACIÓN DE LOS TRIGGERS
-- ---------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_archivo_adjunto_valida ON archivo_adjunto;
CREATE TRIGGER trg_archivo_adjunto_valida BEFORE INSERT OR UPDATE ON archivo_adjunto FOR EACH ROW EXECUTE FUNCTION fn_archivo_adjunto_valida();
DROP TRIGGER IF EXISTS trg_concepto_valida ON concepto_aptitud;
CREATE TRIGGER trg_concepto_valida BEFORE INSERT ON concepto_aptitud FOR EACH ROW EXECUTE FUNCTION fn_concepto_valida();
DROP TRIGGER IF EXISTS trg_hallazgo_valida ON hallazgo;
CREATE TRIGGER trg_hallazgo_valida BEFORE INSERT ON hallazgo FOR EACH ROW EXECUTE FUNCTION fn_hallazgo_valida();
DROP TRIGGER IF EXISTS trg_lectura_valida ON lectura_trampa;
CREATE TRIGGER trg_lectura_valida BEFORE INSERT ON lectura_trampa FOR EACH ROW EXECUTE FUNCTION fn_lectura_valida();
DROP TRIGGER IF EXISTS trg_lote_geometria_valida ON lote_geometria;
CREATE TRIGGER trg_lote_geometria_valida BEFORE INSERT OR UPDATE ON lote_geometria FOR EACH ROW EXECUTE FUNCTION fn_lote_geometria_valida();
DROP TRIGGER IF EXISTS trg_notificacion_valida ON notificacion;
CREATE TRIGGER trg_notificacion_valida BEFORE UPDATE ON notificacion FOR EACH ROW EXECUTE FUNCTION fn_notificacion_valida();
DROP TRIGGER IF EXISTS trg_periodo_valida ON periodo_trampeo;
CREATE TRIGGER trg_periodo_valida BEFORE INSERT OR UPDATE ON periodo_trampeo FOR EACH ROW EXECUTE FUNCTION fn_periodo_valida();
DROP TRIGGER IF EXISTS trg_planificacion_valida ON planificacion;
CREATE TRIGGER trg_planificacion_valida BEFORE INSERT OR UPDATE ON planificacion FOR EACH ROW EXECUTE FUNCTION fn_planificacion_valida();
DROP TRIGGER IF EXISTS trg_planificacion_lote_valida ON planificacion_lote;
CREATE TRIGGER trg_planificacion_lote_valida BEFORE INSERT OR DELETE ON planificacion_lote FOR EACH ROW EXECUTE FUNCTION fn_planificacion_lote_valida();
DROP TRIGGER IF EXISTS trg_planificacion_lote_resultado ON planificacion_lote;
CREATE TRIGGER trg_planificacion_lote_resultado BEFORE UPDATE ON planificacion_lote FOR EACH ROW EXECUTE FUNCTION fn_planificacion_lote_resultado();
DROP TRIGGER IF EXISTS trg_planificacion_notifica ON planificacion;
CREATE TRIGGER trg_planificacion_notifica AFTER INSERT ON planificacion FOR EACH ROW EXECUTE FUNCTION fn_planificacion_notifica();
DROP TRIGGER IF EXISTS trg_operacion_sync_dispositivo_antes ON operacion_sync;
CREATE TRIGGER trg_operacion_sync_dispositivo_antes BEFORE INSERT ON operacion_sync FOR EACH ROW EXECUTE FUNCTION fn_dispositivo_sync();
DROP TRIGGER IF EXISTS trg_operacion_sync_dispositivo ON operacion_sync;
CREATE TRIGGER trg_operacion_sync_dispositivo AFTER INSERT ON operacion_sync FOR EACH ROW EXECUTE FUNCTION fn_dispositivo_sync();
DROP TRIGGER IF EXISTS trg_recepcion_sync_dispositivo ON recepcion_sync;
CREATE TRIGGER trg_recepcion_sync_dispositivo AFTER INSERT ON recepcion_sync FOR EACH ROW EXECUTE FUNCTION fn_dispositivo_sync();
DROP TRIGGER IF EXISTS trg_programa_valida ON programa_inspeccion;
CREATE TRIGGER trg_programa_valida BEFORE INSERT OR UPDATE ON programa_inspeccion FOR EACH ROW EXECUTE FUNCTION fn_programa_valida();
DROP TRIGGER IF EXISTS trg_reticula_inmutable ON reticula;
CREATE TRIGGER trg_reticula_inmutable BEFORE UPDATE ON reticula FOR EACH ROW EXECUTE FUNCTION fn_reticula_inmutable();
DROP TRIGGER IF EXISTS trg_ubicacion_trampa_valida ON ubicacion_trampa;
CREATE TRIGGER trg_ubicacion_trampa_valida BEFORE INSERT OR UPDATE ON ubicacion_trampa FOR EACH ROW EXECUTE FUNCTION fn_ubicacion_trampa_valida();
DROP TRIGGER IF EXISTS trg_usuario_predio_valida ON usuario_predio;
CREATE TRIGGER trg_usuario_predio_valida BEFORE INSERT OR UPDATE ON usuario_predio FOR EACH ROW EXECUTE FUNCTION fn_usuario_predio_valida();
