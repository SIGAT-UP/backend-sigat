"""Módulo NOTIFICACIONES (candidato a extracción, ADR-14).

Los avisos NO los crea ninguna app: los genera el servidor cuando ocurre un
evento (disparadores de planificación en la BD + eventos del backend: revisión,
concepto reemitido, sincronización). El destinatario se deduce del token; nunca
se acepta un usua_id desde la app. Clave de evento única por usuario
(``noti_evento_clave``) para no duplicar.

Frontera de datos: notificacion, categoria_notificacion, preferencia_notificacion,
perfil_usuario.perf_notificaciones_activas.
Push (FCM/APNs) queda FUERA del MVP: hoy el móvil consulta por sondeo / cambios.
"""
