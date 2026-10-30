"""Fixtures comunes. Las pruebas unitarias NO necesitan base de datos."""

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SIGAT_JWT_SECRETO", "solo-pruebas-" + "x" * 40)
os.environ.setdefault("SIGAT_ENTORNO", "pruebas")


@pytest.fixture
def cliente() -> TestClient:
    from sigat_api.main import crear_app

    # Sin `with`: no se ejecuta el ciclo de vida (no abre conexión a la BD).
    return TestClient(crear_app(), raise_server_exceptions=False)
