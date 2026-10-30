"""Módulo IDENTIDAD Y AUTORIZACIÓN.

Responsabilidad: inicio de sesión (local y, a futuro, institucional RI-008),
tokens, recuperación de contraseña, usuarios, roles, asignación de predios y
perfil propio. Aplica el control de acceso por rol EN EL SERVIDOR (RNF-015),
con independencia de lo que muestre cada front.

Frontera de datos (tablas SIGAT de las que es dueño):
    persona, usuario, rol, permiso, rol_permiso, administrador, tecnico,
    productor, usuario_predio, perfil_usuario, restablecimiento_clave
    + esquema propio ``api.sesion_refresco`` (migración 0002).

Lee (sin ser dueño): v_acceso_predio, fn_lotes_visibles.
Necesita de otros módulos (por puertos, ver ``puertos.py``): registrar el
dispositivo del login (sincronización) y validar el archivo de la foto (imágenes).
"""
