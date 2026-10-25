"""Pruebas de los endpoints de salud."""

from fastapi.testclient import TestClient

from ica_api.main import app

client = TestClient(app)


def test_root() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["servicio"] == "ica-durazno-api"


def test_live() -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
