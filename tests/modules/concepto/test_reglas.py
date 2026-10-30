"""Reglas del módulo concepto: pendientes de implementar (cada una cuenta para RNF-017)."""

import pytest

PENDIENTE = pytest.mark.skip(reason="Por implementar")


@pytest.mark.regla
@PENDIENTE
def test_concepto_01() -> None:
    """reemisión usa fecha de efecto = t_observacion del registro disparador."""


@pytest.mark.regla
@PENDIENTE
def test_concepto_02() -> None:
    """concepto a una fecha devuelve el que regía ese día (RF-024)."""


@pytest.mark.regla
@PENDIENTE
def test_concepto_03() -> None:
    """sin umbral el concepto es no_emitido."""
