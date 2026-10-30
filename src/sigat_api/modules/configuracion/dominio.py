"""Reglas puras de configuración (sin BD): se prueban con pytest sin infraestructura."""

import re


def paridad_valida(numero_trampa: int, paridad_tipo: str | None) -> bool:
    """RN-005: Jackson = impar, McPhail = par. ``None`` = el tipo no tiene regla."""
    if paridad_tipo is None:
        return True
    return (numero_trampa % 2 == 1) if paridad_tipo == "impar" else (numero_trampa % 2 == 0)


def reticula_valida(resolucion_m: int, distancia_min_trampas_m: int) -> bool:
    """Arquitectura §5.3 / RN-004: la celda debe superar la distancia mínima entre trampas."""
    return resolucion_m > distancia_min_trampas_m


PATRON_CODIGO_TRAMPA = re.compile(r"^[0-9]{5}-[0-9A-Za-z]{1,10}-[0-9]{1,4}$")
"""Mismo patrón que la restricción ``trampa_codigo_formato`` de la BD: Divipola (5) - ruta - número."""


def numero_desde_codigo(tram_codigo: str) -> int:
    """Número de la trampa = dígitos finales del código (igual que la columna generada ``tram_numero``)."""
    m = re.search(r"([0-9]+)$", tram_codigo)
    if not m:
        raise ValueError("El código no termina en número")
    return int(m.group(1))


def error_codigo_trampa(tram_codigo: str, paridad_tipo: str | None) -> str | None:
    """Mensaje de error del código o None si es válido. Mismas reglas y textos que
    ``sigat.fn_codigo_trampa_error`` (la duplicidad la comprueba el repositorio)."""
    if not PATRON_CODIGO_TRAMPA.fullmatch(tram_codigo):
        return "El código debe tener el formato Divipola-ruta-número, por ejemplo 54518-602-001"
    if not paridad_valida(numero_desde_codigo(tram_codigo), paridad_tipo):
        tipo = "Jackson" if paridad_tipo == "impar" else "McPhail"
        lleva = "impar" if paridad_tipo == "impar" else "par"
        return f"Una trampa {tipo} lleva número {lleva} (RN-005)"
    return None
