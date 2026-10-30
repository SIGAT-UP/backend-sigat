"""Módulo PLANIFICACIÓN.

Flujo de la BD v8 (fn_planificacion_valida, fn_planificacion_lote_resultado):
1. El AGRÓNOMO crea una planificación para un PRODUCTOR (documento o observación >= 10).
2. El PRODUCTOR la acepta o la rechaza (motivo >= 10). Solo el destinatario, solo si pendiente.
3. Con la planificación ACEPTADA, el agrónomo crea ACTIVIDADES para TÉCNICOS
   (``plan_id_origen`` obligatorio) con sus lotes. El técnico NO acepta ni rechaza.
4. El técnico registra el resultado por lote (``planificacion_lote``): ejecutada /
   no_ejecutada (justificación obligatoria), una sola vez. En línea o por sync (C02/C03).
5. Al resolverse todos los lotes, la actividad pasa a ``completada``.
Avisos: disparadores fn_planificacion_notifica y fn_planificacion_respuesta_notifica (C04).

Frontera de datos: planificacion, planificacion_lote.
"""
