"""Reglas del módulo notificaciones: pendientes de implementar (cada una cuenta para RNF-017)."""

import pytest

PENDIENTE = pytest.mark.skip(reason="Por implementar")


@pytest.mark.regla
@PENDIENTE
def test_notificaciones_01() -> None:
    """solo se listan los avisos del actor."""


@pytest.mark.regla
@PENDIENTE
def test_notificaciones_02() -> None:
    """marcar leído un aviso ajeno responde 404."""


@pytest.mark.regla
@PENDIENTE
def test_notificaciones_03() -> None:
    """un mismo evento no crea dos avisos."""
