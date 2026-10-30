"""Reglas del módulo configuracion: pendientes de implementar (cada una cuenta para RNF-017)."""

import pytest

PENDIENTE = pytest.mark.skip(reason="Por implementar")


@pytest.mark.regla
@PENDIENTE
def test_configuracion_01() -> None:
    """código de trampa duplicado da 409 'Duplicidad de código de trampa'."""


@pytest.mark.regla
@PENDIENTE
def test_configuracion_02() -> None:
    """nueva versión del programa no altera periodos ya calculados (ADR-05)."""


@pytest.mark.regla
@PENDIENTE
def test_configuracion_03() -> None:
    """retícula menor o igual a la distancia mínima se rechaza (§5.3)."""


@pytest.mark.regla
@PENDIENTE
def test_configuracion_04() -> None:
    """búsqueda de trampa inexistente responde en_catalogo=false (no 404)."""


@pytest.mark.regla
@PENDIENTE
def test_configuracion_05() -> None:
    """trampa fuera del lote ADVIERTE y no bloquea (RF-012)."""


@pytest.mark.regla
@PENDIENTE
def test_configuracion_06() -> None:
    """paquete de campo responde 304 con If-None-Match vigente."""
