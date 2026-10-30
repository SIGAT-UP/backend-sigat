"""RNF-015: la matriz de permisos refleja las reglas de la BD v8."""

from sigat_api.compartido.tipos import RolCodigo as R
from sigat_api.modules.identidad.permisos import permitido


def test_solo_el_agronomo_crea_planificaciones() -> None:
    assert permitido("planificacion.crear", R.AGRONOMO_SUPERVISOR)
    assert not any(permitido("planificacion.crear", r) for r in (R.ADMINISTRADOR, R.TECNICO, R.PRODUCTOR))


def test_el_tecnico_no_responde_planificaciones() -> None:
    assert not permitido("planificacion.responder", R.TECNICO)
    assert permitido("planificacion.responder", R.PRODUCTOR)


def test_permiso_desconocido_se_niega() -> None:
    assert not permitido("no.existe", R.ADMINISTRADOR)
