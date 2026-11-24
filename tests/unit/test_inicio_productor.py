"""GET /api/v1/yo/inicio con rol PRODUCTOR (PW01) y GET /api/v1/productor/cultivo (sigue en 501).

Comprueba la respuesta contra el modelo del contrato OpenAPI (``InicioResumen``).
"""

import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from pydantic import SecretStr

from sigat_api.api.fabricas import (
    servicio_concepto,
    servicio_lotes,
    servicio_notificaciones,
    servicio_planificacion,
    servicio_revision,
)
from sigat_api.api.v1.esquemas_compuestos import InicioResumen
from sigat_api.compartido.errores import NoImplementado
from sigat_api.compartido.tipos import Cliente, RolCodigo
from sigat_api.config import Configuracion
from sigat_api.infra.seguridad.tokens import ServicioTokens
from sigat_api.modules.concepto.servicio import InicioProductorDatos

VISITA = datetime(2026, 10, 8, 14, 20, tzinfo=UTC)


def _token(rol: RolCodigo, usua_id: int) -> str:
    cfg = Configuracion(jwt_secreto=SecretStr(os.environ["SIGAT_JWT_SECRETO"]))
    token, _ = ServicioTokens(cfg).emitir_acceso(usua_id, rol, None, Cliente.WEB)
    return token


def _sustituir(cliente: TestClient, concepto: AsyncMock) -> dict[str, AsyncMock]:
    otros = {"notis": AsyncMock(), "revision": AsyncMock(), "planif": AsyncMock(), "lotes": AsyncMock()}
    otros["notis"].conteo.return_value.no_leidas = 1
    app = cliente.app
    app.dependency_overrides[servicio_notificaciones] = lambda: otros["notis"]  # type: ignore[attr-defined]
    app.dependency_overrides[servicio_revision] = lambda: otros["revision"]  # type: ignore[attr-defined]
    app.dependency_overrides[servicio_planificacion] = lambda: otros["planif"]  # type: ignore[attr-defined]
    app.dependency_overrides[servicio_lotes] = lambda: otros["lotes"]  # type: ignore[attr-defined]
    app.dependency_overrides[servicio_concepto] = lambda: concepto  # type: ignore[attr-defined]
    return otros


def test_inicio_productor_devuelve_sus_indicadores(cliente: TestClient) -> None:
    concepto = AsyncMock()
    concepto.inicio_productor.return_value = InicioProductorDatos(
        lotes=4, planificaciones_por_responder=2, ultima_visita=VISITA
    )
    otros = _sustituir(cliente, concepto)

    r = cliente.get(
        "/api/v1/yo/inicio", headers={"Authorization": f"Bearer {_token(RolCodigo.PRODUCTOR, 7)}"}
    )

    assert r.status_code == 200
    datos = r.json()
    InicioResumen.model_validate(datos)  # cumple el contrato
    assert datos["rol"] == "PRODUCTOR"
    assert datos["productor"] == {
        "lotes": 4,
        "planificaciones_por_responder": 2,
        "ultimo_mtd": None,  # sin criterio aprobado para elegir un MTD entre lotes
        "ultima_visita": "2026-10-08T14:20:00Z",
    }
    assert datos["agronomo"] is None
    assert datos["tecnico"] is None
    actor = concepto.inicio_productor.await_args.args[0]
    assert (actor.usua_id, actor.rol) == (7, RolCodigo.PRODUCTOR)  # siempre el del token
    otros["planif"].contar_pendientes.assert_not_called()  # no usa los indicadores del agrónomo


def test_inicio_de_otros_roles_no_calcula_el_bloque_productor(cliente: TestClient) -> None:
    concepto = AsyncMock()
    _sustituir(cliente, concepto)
    for rol in (RolCodigo.TECNICO, RolCodigo.ADMINISTRADOR):
        r = cliente.get("/api/v1/yo/inicio", headers={"Authorization": f"Bearer {_token(rol, 1)}"})
        assert r.status_code == 200
        assert r.json()["productor"] is None
    concepto.inicio_productor.assert_not_called()


def test_cultivo_responde_501_mientras_falte_lotes_revisados(cliente: TestClient) -> None:
    concepto = AsyncMock()
    concepto.cultivo_productor.side_effect = NoImplementado(
        "Cultivo del productor: falta la definición oficial de lotes_revisados (pendiente del Owner)"
    )
    _sustituir(cliente, concepto)

    r = cliente.get(
        "/api/v1/productor/cultivo", headers={"Authorization": f"Bearer {_token(RolCodigo.PRODUCTOR, 7)}"}
    )

    assert r.status_code == 501
    assert r.headers["content-type"].startswith("application/problem+json")


def test_cultivo_exige_permiso_de_productor(cliente: TestClient) -> None:
    concepto = AsyncMock()
    _sustituir(cliente, concepto)
    r = cliente.get(
        "/api/v1/productor/cultivo", headers={"Authorization": f"Bearer {_token(RolCodigo.TECNICO, 1)}"}
    )
    assert r.status_code == 403
    concepto.cultivo_productor.assert_not_called()
