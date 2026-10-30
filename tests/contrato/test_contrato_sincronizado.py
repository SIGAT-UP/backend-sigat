"""Puerta de contrato (Arquitectura §9.3): contracts/openapi.json debe coincidir con el código."""

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def test_openapi_versionado_coincide_con_el_codigo() -> None:
    r = subprocess.run(
        [sys.executable, str(RAIZ / "scripts" / "exportar_openapi.py"), "--verificar"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
