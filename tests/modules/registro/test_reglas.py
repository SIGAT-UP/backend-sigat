"""Reglas del módulo registro: pendientes de implementar (cada una cuenta para RNF-017)."""

import pytest

PENDIENTE = pytest.mark.skip(reason="Por implementar")


@pytest.mark.regla
@PENDIENTE
def test_registro_01() -> None:
    """R-T1 orden canónico por t_observacion y desempate (t_captura, id)."""


@pytest.mark.regla
@PENDIENTE
def test_registro_02() -> None:
    """R-T2 alta con t_observacion anterior a la última es alta_retroactiva."""


@pytest.mark.regla
@PENDIENTE
def test_registro_03() -> None:
    """R-T3 corrección crea versión n+1 y conserva la anterior."""


@pytest.mark.regla
@PENDIENTE
def test_registro_04() -> None:
    """ADR-02 corrección que cambia t_observacion se rechaza."""


@pytest.mark.regla
@PENDIENTE
def test_registro_05() -> None:
    """R-T5 solapamiento queda en revisar y no elige ganador."""


@pytest.mark.regla
@PENDIENTE
def test_registro_06() -> None:
    """fecha de observación futura se rechaza."""


@pytest.mark.regla
@PENDIENTE
def test_registro_07() -> None:
    """trampa que no pertenecía al lote en t_observacion se rechaza."""


@pytest.mark.regla
@PENDIENTE
def test_registro_08() -> None:
    """lectura no leída exige justificación y especímenes nulos."""


@pytest.mark.regla
@PENDIENTE
def test_registro_09() -> None:
    """MTD = M/(T×D) y T×D=0 da nulo."""


@pytest.mark.regla
@PENDIENTE
def test_registro_10() -> None:
    """sin umbral vigente a la fecha del periodo el contraste es sin_umbral."""


@pytest.mark.regla
@PENDIENTE
def test_registro_11() -> None:
    """aceptar una revisión ya aceptada da 409."""
