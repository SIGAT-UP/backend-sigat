"""Matriz de permisos por rol (RNF-015). ÚNICA fuente de verdad del backend.

La BD tiene ``permiso`` / ``rol_permiso`` sin valores oficiales todavía
(pendiente institucional). Mientras tanto, la matriz vive aquí como CÓDIGO
revisable; cuando se carguen los permisos oficiales, ``ServicioAutorizacion`` los lee
de la BD y esta tabla pasa a ser la semilla documentada.

Además del rol, TODA consulta de lotes/predios se restringe con
``fn_lotes_visibles(usua_id)``: el rol dice QUÉ puede hacer; la asignación
(``usuario_predio`` / propiedad del predio / planificación) dice SOBRE QUÉ.
"""

from sigat_api.compartido.tipos import RolCodigo

A = RolCodigo.ADMINISTRADOR
G = RolCodigo.AGRONOMO_SUPERVISOR
T = RolCodigo.TECNICO
P = RolCodigo.PRODUCTOR

TODOS = frozenset({A, G, T, P})

PERMISOS: dict[str, frozenset[RolCodigo]] = {
    # identidad
    "usuarios.administrar": frozenset({A}),
    "auditoria.consultar": frozenset({A}),
    # catálogos y configuración
    "catalogos.consultar": TODOS,
    "catalogos.editar": frozenset({A, G}),
    "predios.consultar": TODOS,
    "predios.editar": frozenset({A}),
    "lotes.editar": frozenset({A, G}),
    "trampas.editar": frozenset({A, G}),
    "programa.consultar": TODOS,
    "programa.versionar": frozenset({G}),
    "reticula.crear": frozenset({A, G}),
    "paquete_campo.descargar": frozenset({T, G, P}),
    # registro
    "visitas.consultar": frozenset({A, G, T}),
    "lecturas.consultar": frozenset({A, G, T, P}),
    "lecturas.corregir": frozenset({G}),
    "revisiones.resolver": frozenset({G}),
    "autorreporte.registrar": frozenset({P}),
    "autorreporte.consultar": frozenset({A, G, P}),
    # sincronización
    "sincronizacion.enviar": frozenset({T, P}),
    # concepto
    "concepto.consultar": TODOS,
    # planificación
    "planificacion.crear": frozenset({G}),
    "planificacion.responder": frozenset({P}),
    "planificacion.resultado_lote": frozenset({T}),
    "planificacion.consultar": frozenset({G, T, P}),
    "actividades_tecnico.consultar": frozenset({A, G}),
}


def permitido(permiso: str, rol: RolCodigo) -> bool:
    return rol in PERMISOS.get(permiso, frozenset())
