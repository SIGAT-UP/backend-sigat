"""R-T4: la huella del contenido es estable e ignora lo que no es contenido."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

from sigat_api.modules.sincronizacion import huella


def _op(**cambios: object) -> SimpleNamespace:
    base = {
        "entidad": "lectura_trampa",
        "accion": "crear",
        "registro_id": UUID("0190f5b0-0000-7000-8000-000000000001"),
        "version": 1,
        "linaje": "inspeccion_oficial",
        "t_observacion": datetime(2026, 9, 15, 14, 40, tzinfo=UTC),
        "datos": {"lect_especimenes": 3, "tram_id": 7},
    }
    base.update(cambios)
    return SimpleNamespace(**base)


def test_orden_de_claves_no_cambia_la_huella() -> None:
    a = huella.calcular(huella.contenido_canonico(_op(datos={"lect_especimenes": 3, "tram_id": 7})))
    b = huella.calcular(huella.contenido_canonico(_op(datos={"tram_id": 7, "lect_especimenes": 3})))
    assert a == b


def test_contenido_distinto_cambia_la_huella() -> None:
    a = huella.calcular(huella.contenido_canonico(_op()))
    b = huella.calcular(huella.contenido_canonico(_op(datos={"lect_especimenes": 4, "tram_id": 7})))
    assert a != b
