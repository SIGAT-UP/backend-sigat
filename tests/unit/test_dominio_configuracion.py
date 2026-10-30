"""RN-005 y Arquitectura §5.3 (reglas puras)."""

import pytest

from sigat_api.modules.configuracion.dominio import error_codigo_trampa, paridad_valida, reticula_valida


@pytest.mark.regla
@pytest.mark.parametrize(
    ("numero", "paridad", "esperado"),
    [(1, "impar", True), (2, "impar", False), (2, "par", True), (3, "par", False), (4, None, True)],
)
def test_paridad_rn005(numero: int, paridad: str | None, esperado: bool) -> None:
    assert paridad_valida(numero, paridad) is esperado


@pytest.mark.regla
def test_reticula_debe_superar_distancia_minima() -> None:
    assert reticula_valida(80, 60)
    assert not reticula_valida(40, 60)
    assert not reticula_valida(60, 60)


@pytest.mark.regla
@pytest.mark.parametrize(
    ("codigo", "paridad", "esperado"),
    [
        ("54518-602-011", "impar", None),
        ("54518-602-012", "impar", "Una trampa Jackson lleva número impar (RN-005)"),
        ("54518-602-012", "par", None),
        ("54518-602-013", "par", "Una trampa McPhail lleva número par (RN-005)"),
        (
            "ICA-001",
            "impar",
            "El código debe tener el formato Divipola-ruta-número, por ejemplo 54518-602-001",
        ),
        (
            "5451-602-1",
            None,
            "El código debe tener el formato Divipola-ruta-número, por ejemplo 54518-602-001",
        ),
    ],
)
def test_codigo_trampa_mismas_reglas_que_la_bd(
    codigo: str, paridad: str | None, esperado: str | None
) -> None:
    assert error_codigo_trampa(codigo, paridad) == esperado
