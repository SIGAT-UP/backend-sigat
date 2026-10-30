"""Reglas del módulo planificacion: pendientes de implementar (cada una cuenta para RNF-017)."""

import pytest

PENDIENTE = pytest.mark.skip(reason="Por implementar")


@pytest.mark.regla
@PENDIENTE
def test_planificacion_01() -> None:
    """solo el agrónomo crea (C01: creador = actor)."""


@pytest.mark.regla
@PENDIENTE
def test_planificacion_02() -> None:
    """planificación a productor exige documento u observación >= 10."""


@pytest.mark.regla
@PENDIENTE
def test_planificacion_03() -> None:
    """actividad de técnico exige plan_id_origen ACEPTADA y al menos un lote."""


@pytest.mark.regla
@PENDIENTE
def test_planificacion_04() -> None:
    """solo el productor destinatario responde y solo si pendiente."""


@pytest.mark.regla
@PENDIENTE
def test_planificacion_05() -> None:
    """rechazo exige motivo >= 10."""


@pytest.mark.regla
@PENDIENTE
def test_planificacion_06() -> None:
    """no_ejecutada exige justificación; un lote se resuelve una vez."""


@pytest.mark.regla
@PENDIENTE
def test_planificacion_07() -> None:
    """al resolver todos los lotes la actividad pasa a completada."""
