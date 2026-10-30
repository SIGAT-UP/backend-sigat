"""Reglas del módulo catalogo: pendientes de implementar (cada una cuenta para RNF-017)."""

import pytest

PENDIENTE = pytest.mark.skip(reason="Por implementar")


@pytest.mark.regla
@PENDIENTE
def test_catalogo_01() -> None:
    """valores repetidos sin distinguir mayúsculas se rechazan."""


@pytest.mark.regla
@PENDIENTE
def test_catalogo_02() -> None:
    """un valor en uso ausente del reemplazo se retira, no se borra."""


@pytest.mark.regla
@PENDIENTE
def test_catalogo_03() -> None:
    """guardar un catálogo invalida los paquetes de campo."""
