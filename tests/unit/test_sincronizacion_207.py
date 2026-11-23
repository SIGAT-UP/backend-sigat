"""POST /sincronizacion/lotes responde 207 Multi-Status (decisión del Owner, HU-02)."""

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from sigat_api.api.fabricas import servicio_sincronizacion
from sigat_api.compartido.errores import Prohibido
from sigat_api.compartido.tipos import Actor, Cliente, ResultadoSync, RolCodigo
from sigat_api.config import obtener_configuracion
from sigat_api.infra.seguridad.tokens import ServicioTokens
from sigat_api.modules.sincronizacion import esquemas as e

RUTA = "/api/v1/sincronizacion/lotes"
DISP = UUID("0190f5b0-0000-7000-8000-0000000000aa")
AHORA = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)


class ServicioFalso:
    def __init__(self, resultados: list[ResultadoSync] | None = None, error: Exception | None = None) -> None:
        self._resultados = resultados or []
        self._error = error

    async def recibir(self, actor: Actor, lote: e.LoteSincronizacion) -> e.RespuestaLote:
        if self._error:
            raise self._error
        return e.RespuestaLote(
            resultados=[
                e.ResultadoOperacion(
                    cliente_id=op.cliente_id,
                    oper_id=None,
                    resultado=resultado,
                    motivo=None,
                    codigo=None,
                    registro_id=op.registro_id,
                    version=op.version,
                    reproceso="no_aplica",
                    fecha_efecto=None,
                    reintentable=False,
                )
                for op, resultado in zip(lote.operaciones, self._resultados, strict=True)
            ],
            cursor=AHORA.isoformat(),
            servidor_utc=AHORA,
        )


def _operacion() -> dict[str, Any]:
    return {
        "cliente_id": str(uuid4()),
        "entidad": "lectura_trampa",
        "accion": "crear",
        "registro_id": str(uuid4()),
        "version": 1,
        "t_observacion": AHORA.isoformat(),
        "t_captura": AHORA.isoformat(),
        "hash_contenido": "a" * 64,
        "datos": {},
    }


def _lote(n: int) -> dict[str, Any]:
    return {
        "disp_id": str(DISP),
        "enviado_en": AHORA.isoformat(),
        "operaciones": [_operacion() for _ in range(n)],
    }


def _cabeceras() -> dict[str, str]:
    jwt, _ = ServicioTokens(obtener_configuracion()).emitir_acceso(7, RolCodigo.TECNICO, DISP, Cliente.MOVIL)
    return {"Authorization": f"Bearer {jwt}"}


@pytest.fixture
def con_servicio(cliente: TestClient) -> Iterator[Any]:
    def instalar(servicio: ServicioFalso) -> TestClient:
        cliente.app.dependency_overrides[servicio_sincronizacion] = lambda: servicio  # type: ignore[attr-defined]
        return cliente

    yield instalar
    cliente.app.dependency_overrides.clear()  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "resultados",
    [
        [ResultadoSync.ALTA_NUEVA, ResultadoSync.IDEMPOTENTE_REPETIDA],
        [ResultadoSync.ALTA_NUEVA, ResultadoSync.RECHAZADA],
        [ResultadoSync.RECHAZADA, ResultadoSync.CONFLICTO_CONTENIDO],
    ],
    ids=["todas_aceptadas", "algunas_rechazadas", "todas_rechazadas"],
)
def test_lote_leido_responde_207_con_un_resultado_por_operacion(
    con_servicio: Any, resultados: list[ResultadoSync]
) -> None:
    r = con_servicio(ServicioFalso(resultados)).post(RUTA, headers=_cabeceras(), json=_lote(2))

    assert r.status_code == 207
    assert [x["resultado"] for x in r.json()["resultados"]] == [x.value for x in resultados]


def test_dispositivo_ajeno_rechaza_el_lote_completo_con_403(con_servicio: Any) -> None:
    error = Prohibido("El lote no corresponde al dispositivo de la sesión.", codigo="DISPOSITIVO_NO_COINCIDE")
    r = con_servicio(ServicioFalso(error=error)).post(RUTA, headers=_cabeceras(), json=_lote(1))

    assert (r.status_code, r.json()["codigo"]) == (403, "DISPOSITIVO_NO_COINCIDE")


def test_lote_vacio_o_sin_sesion_no_llega_a_procesarse(con_servicio: Any) -> None:
    cliente = con_servicio(ServicioFalso())

    assert cliente.post(RUTA, headers=_cabeceras(), json=_lote(0)).status_code == 422
    assert cliente.post(RUTA, json=_lote(1)).status_code == 401


def test_el_contrato_documenta_207(cliente: TestClient) -> None:
    respuestas = cliente.get("/api/v1/openapi.json").json()["paths"][RUTA]["post"]["responses"]

    assert "207" in respuestas
    assert "200" not in respuestas
