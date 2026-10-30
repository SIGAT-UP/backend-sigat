"""Módulo AUDITORÍA (consulta).

La ESCRITURA de la bitácora la hace la BD (disparador ``fn_auditar``, SECURITY
DEFINER, append-only) con ``fn_usuario_actual()``; el backend añade entradas
``ACCESO`` (lectura de datos personales, ADR-11) y ``SYNC``. Este módulo solo
CONSULTA para el administrador (RF-083) y nunca expone contraseñas ni hashes.

Frontera de datos: bitacora_auditoria (solo lectura + INSERT de ACCESO/SYNC).
"""
