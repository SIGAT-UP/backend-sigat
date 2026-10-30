"""Proveedor de identidad institucional (RI-008 / Arquitectura §6.1).

La organización no debe administrar aquí las credenciales de sus empleados: cuando
``usuario.usua_proveedor = 'externo'`` la autenticación se delega a un emisor
OIDC (``SIGAT_OIDC_EMISOR``) y ``usua_sujeto_externo`` guarda el ``sub``.

Pendiente (pregunta abierta, no se decide aquí): qué proveedor, qué flujo
(Authorization Code + PKCE para web y móvil) y cómo se mapean los grupos a roles.
"""

from sigat_api.compartido.errores import NoImplementado


async def intercambiar_codigo(codigo: str, verificador_pkce: str, redireccion: str) -> dict[str, str]:
    """Intercambia el código de autorización por los tokens del proveedor y devuelve sus reclamos."""
    raise NoImplementado("Inicio de sesión con el proveedor institucional (RI-008)")
