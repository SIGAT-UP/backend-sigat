"""Reglas del módulo auditoria: pendientes de implementar (cada una cuenta para RNF-017)."""

import pytest

PENDIENTE = pytest.mark.skip(reason="Por implementar")


@pytest.mark.regla
@PENDIENTE
def test_auditoria_01() -> None:
    """solo el administrador consulta la bitácora."""


@pytest.mark.regla
@PENDIENTE
def test_auditoria_02() -> None:
    """la bitácora nunca expone contraseñas ni hashes."""
