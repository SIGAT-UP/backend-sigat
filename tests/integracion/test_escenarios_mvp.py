"""Escenarios que cierran los hitos del MVP (Tabla de prioridades §7). Requieren BD SIGAT v8."""

import pytest

pytestmark = [pytest.mark.integracion, pytest.mark.skip(reason="Por implementar: requiere BD SIGAT v8")]


def test_visita_completa_en_modo_avion_y_carga_posterior() -> None:
    """RF-060/061: visita entera sin red; al reconectar el lote se acepta sin pérdida ni duplicados."""


def test_alta_retroactiva_entra_en_su_posicion_real() -> None:
    """RF-065/054: llega el lunes después del viernes; la serie se reordena y el concepto se reemite."""


def test_mismo_envio_tres_veces_no_duplica() -> None:
    """RF-064: el mismo lote enviado tres veces deja exactamente las mismas filas."""


def test_historico_identico_antes_y_despues_de_reprocesar() -> None:
    """RNF-009: reprocesar un periodo sin cambios no altera el histórico."""
