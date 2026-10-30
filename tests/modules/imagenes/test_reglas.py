"""Reglas del módulo imagenes: pendientes de implementar (cada una cuenta para RNF-017)."""

import pytest

PENDIENTE = pytest.mark.skip(reason="Por implementar")


@pytest.mark.regla
@PENDIENTE
def test_imagenes_01() -> None:
    """archivo con hash distinto al declarado queda rechazado."""


@pytest.mark.regla
@PENDIENTE
def test_imagenes_02() -> None:
    """MIME se valida por contenido y no por extensión."""


@pytest.mark.regla
@PENDIENTE
def test_imagenes_03() -> None:
    """foto de otro usuario no puede usarse como foto de perfil."""
