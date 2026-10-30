-- =====================================================================
-- SIGAT v9.1 - Categoría de aviso «Solicitudes de cuenta»
--
-- Qué cambia: SOLO AGREGA un valor al catálogo categoria_notificacion. No borra ni
-- modifica tablas, columnas, relaciones ni datos existentes.
-- Por qué: cuando alguien usa «¿Problemas para ingresar?» en la web o el móvil, el
-- backend crea un aviso de esta categoría para cada administrador activo, que entra a
-- Usuarios y asigna la contraseña nueva (decisión del 29/10/2026).
-- Idempotente: se puede ejecutar varias veces. En una base existente lo aplica
-- migracion/M9_v9_a_v9_1.sql (paquete de BD) o la migración Alembic 0003 (backend).
-- =====================================================================
SET search_path = sigat, public;

INSERT INTO categoria_notificacion (cate_codigo, cate_descripcion)
VALUES ('solicitudes_cuenta', 'Solicitudes de cuenta')
ON CONFLICT (cate_codigo) DO NOTHING;
