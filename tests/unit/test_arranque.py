"""El esqueleto arranca, publica el contrato y responde con problem+json."""

from fastapi.testclient import TestClient

PREFIJO = "/api/v1"


def test_salud_responde_ok(cliente: TestClient) -> None:
    r = cliente.get(f"{PREFIJO}/salud")
    assert r.status_code == 200
    assert r.json() == {"estado": "ok"}


def test_ruta_protegida_sin_token_da_401_problem_json(cliente: TestClient) -> None:
    r = cliente.get(f"{PREFIJO}/lotes")
    assert r.status_code == 401
    assert r.headers["content-type"].startswith("application/problem+json")
    cuerpo = r.json()
    assert cuerpo["codigo"] == "TOKEN_AUSENTE"
    assert "traza_id" in cuerpo


def test_validacion_devuelve_errores_por_campo(cliente: TestClient) -> None:
    from collections.abc import AsyncIterator

    from sigat_api.api.dependencias import conexion_publica

    async def sin_bd() -> AsyncIterator[None]:  # patrón para probar rutas sin PostgreSQL
        yield None

    cliente.app.dependency_overrides[conexion_publica] = sin_bd  # type: ignore[attr-defined]
    r = cliente.post(f"{PREFIJO}/auth/login", json={"usuario": "x"})
    assert r.status_code == 422
    assert r.json()["codigo"] == "VALIDACION"
    assert r.json()["errores"]


def test_openapi_expone_los_grupos_de_ambos_fronts(cliente: TestClient) -> None:
    rutas = cliente.get(f"{PREFIJO}/openapi.json").json()["paths"]
    for esperada in (
        "/api/v1/auth/login",
        "/api/v1/sincronizacion/lotes",
        "/api/v1/predios/{pred_id}/paquete-campo/contenido",
        "/api/v1/revisiones/{visi_id}/aceptacion",
        "/api/v1/planificaciones/{plan_id}/rechazo",
        "/api/v1/productor/cultivo",
        "/api/v1/auditoria",
    ):
        assert esperada in rutas
