# Política de seguridad — sigat-durazno-api

## Cómo reportar una vulnerabilidad

No abra un issue público. Escriba al responsable de seguridad del proyecto por un canal privado con: descripción, pasos para reproducir, impacto y versión o commit afectado. No incluya datos personales reales en el reporte.

## Controles vigentes (verificados en la auditoría del 2026-10-30)

- Contraseñas con argon2id; ninguna cuenta por defecto (el primer administrador se crea por consola).
- Token de acceso de 15 minutos y refresco rotativo con detección de reutilización; bloqueo por intentos (5 por usuario, 30 por IP en 15 minutos).
- Permisos por rol en cada ruta (`requiere("…")`) y errores `problem+json` sin detalles internos.
- Cookie de refresco HttpOnly, `SameSite=Strict`, `Secure` configurable (`SIGAT_COOKIE_SEGURA=true` en producción).
- CI: `pip-audit`, `detect-secrets`, revisión de migraciones destructivas, contrato OpenAPI sincronizado.

## Pendientes conocidos

- Visibilidad por predio (`exigir_lote_visible`) sin implementar: hasta entonces, las rutas de datos de campo responden 501.
- Proveedor de identidad institucional (OIDC) sin implementar.
- Usuario de base de datos con privilegios mínimos para producción: definir y aplicar.
