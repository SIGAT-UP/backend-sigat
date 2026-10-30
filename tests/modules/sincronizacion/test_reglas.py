"""Reglas del módulo sincronizacion: pendientes de implementar (cada una cuenta para RNF-017)."""

import pytest

PENDIENTE = pytest.mark.skip(reason="Por implementar")


@pytest.mark.regla
@PENDIENTE
def test_sincronizacion_01() -> None:
    """R-T4 mismo cliente_id y mismo hash es idempotente_repetida sin duplicar."""


@pytest.mark.regla
@PENDIENTE
def test_sincronizacion_02() -> None:
    """mismo cliente_id con hash distinto es conflicto_contenido."""


@pytest.mark.regla
@PENDIENTE
def test_sincronizacion_03() -> None:
    """lote parcialmente aceptado responde por operación."""


@pytest.mark.regla
@PENDIENTE
def test_sincronizacion_04() -> None:
    """revisar/rechazada tienen reintentable=false."""


@pytest.mark.regla
@PENDIENTE
def test_sincronizacion_05() -> None:
    """R-T6 deriva de reloj sin confirmación queda en revisar."""


@pytest.mark.regla
@PENDIENTE
def test_sincronizacion_06() -> None:
    """disp_id distinto al del token rechaza el lote con 403."""


@pytest.mark.regla
@PENDIENTE
def test_sincronizacion_07() -> None:
    """alta retroactiva encola reproceso con clave única por periodo."""
