"""POST /aplicaciones y POST /cosechas (HU-01) contra PostgreSQL REAL, por la API.

Requiere ``SIGAT_DB_URL_PRUEBAS`` (ver ``conftest.py``). Usa bases TEMPORALES que se borran al final.
Ana (productora) tiene los lotes 11 y 12; Bruno, el 21. Los tokens se emiten como lo hace el login.
"""

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import asyncpg
import pytest
from fastapi.testclient import TestClient

from sigat_api.compartido.tipos import Cliente, RolCodigo

pytestmark = pytest.mark.integracion

P = "/api/v1"
TECNICO, ANA = 1, 2
DISP_ANA = "00000000-0000-0000-0000-0000000000d2"
DISP_TECNICO = "00000000-0000-0000-0000-0000000000d1"
AYER = (datetime.now(UTC) - timedelta(days=1)).isoformat()

DATOS = r"""
SET search_path = sigat, public;
INSERT INTO region (regi_id, regi_descripcion) VALUES (1, 'Región de prueba');
INSERT INTO departamento (depa_id, depa_descripcion, regi_id, depa_codigo) VALUES (1, 'Depto', 1, '99');
INSERT INTO municipio (muni_id, muni_descripcion, depa_id, muni_codigo) VALUES (1, 'Muni', 1, '001');
INSERT INTO centro_acopio (cent_id, cent_descripcion, depa_id) VALUES (1, 'Centro', 1);
INSERT INTO persona (pers_cc, pers_nombre, pers_apellido) VALUES
  (1001, 'Adela', 'Admin'), (1002, 'Tomás', 'Técnico'), (2001, 'Ana', 'Productora'), (2002, 'Bruno', 'Productor');
INSERT INTO administrador (admi_id, pers_cc, cent_id) VALUES (1, 1001, 1);
INSERT INTO tecnico (tecn_id, pers_cc, cent_id, admi_id, tecn_fecha_registro, esta_id)
  VALUES (1, 1002, 1, 1, DATE '2026-01-01', (SELECT esta_id FROM estado_registro WHERE esta_descripcion = 'activo'));
INSERT INTO productor (pers_cc, prod_fecha_registro, prod_tecnico_registro_id, muni_id) VALUES
  (2001, DATE '2026-01-01', 1, 1), (2002, DATE '2026-01-01', 1, 1);
INSERT INTO usuario (usua_id, pers_cc, usua_usuario, usua_requiere_reinicio, rol_id, esta_id)
SELECT v.id, v.cc, v.usu, true, r.rol_id, e.esta_id
  FROM (VALUES (1, 1002::bigint, 'tecnico.prueba', 'TECNICO'),
               (2, 2001::bigint, 'ana.prueba', 'PRODUCTOR'),
               (3, 2002::bigint, 'bruno.prueba', 'PRODUCTOR')) v(id, cc, usu, rol)
  JOIN rol r ON r.rol_codigo = v.rol
  JOIN estado_registro e ON e.esta_descripcion = 'activo';
INSERT INTO predio (pred_id, pred_nombre, muni_id, pred_area, pers_cc, pred_fecha_registro, pred_tecnico_registro_id)
  VALUES (1, 'Predio Ana', 1, 10, 2001, DATE '2026-01-01', 1), (2, 'Predio Bruno', 1, 10, 2002, DATE '2026-01-01', 1);
INSERT INTO lote (lote_id, lote_codigo, lote_descripcion, lote_area, pred_id, lote_fecha_registro, lote_tecnico_registro_id) VALUES
  (11, 'L11', 'Lote 1 · Norte', 2, 1, DATE '2026-01-01', 1),
  (12, 'L12', 'Lote 2 · Centro', 2, 1, DATE '2026-01-01', 1),
  (21, 'L21', 'Lote único', 2, 2, DATE '2026-01-01', 1);
INSERT INTO dispositivo (disp_id, disp_plataforma) VALUES
  ('00000000-0000-0000-0000-0000000000d1', 'android'), ('00000000-0000-0000-0000-0000000000d2', 'otro');
"""


def _ejecutar(h: SimpleNamespace, nombre: str, sql: str) -> None:
    async def _correr() -> None:
        con = await asyncpg.connect(str(h.url(nombre)).replace("postgresql+asyncpg://", "postgresql://", 1))
        try:
            await con.execute(sql)
        finally:
            await con.close()

    asyncio.run(_correr())


@pytest.fixture(scope="module")
def bd(h: SimpleNamespace) -> Iterator[str]:
    nombre = h.crear_bd()
    try:
        r = h.alembic(nombre, "upgrade", "head")
        assert r.returncode == 0, r.stderr
        _ejecutar(h, nombre, DATOS)
        yield nombre
    finally:
        h.borrar_bd(nombre)


@pytest.fixture(scope="module")
def api(bd: str, h: SimpleNamespace) -> Iterator[TestClient]:
    from sigat_api.config import obtener_configuracion
    from sigat_api.infra.db import motor

    mp = pytest.MonkeyPatch()
    mp.setenv("SIGAT_DB_URL", h.url(bd))
    obtener_configuracion.cache_clear()
    motor._motor = None
    from sigat_api.main import crear_app

    with TestClient(crear_app()) as c:
        yield c
    mp.undo()
    obtener_configuracion.cache_clear()
    motor._motor = None


def _token(usua_id: int, rol: RolCodigo, disp: str) -> dict[str, str]:
    from uuid import UUID

    from sigat_api.config import obtener_configuracion
    from sigat_api.infra.seguridad.tokens import ServicioTokens

    jwt, _ = ServicioTokens(obtener_configuracion()).emitir_acceso(usua_id, rol, UUID(disp), Cliente.WEB)
    return {"Authorization": f"Bearer {jwt}"}


def _ana() -> dict[str, str]:
    return _token(ANA, RolCodigo.PRODUCTOR, DISP_ANA)


def _unidad(h: SimpleNamespace, bd: str, simbolo: str) -> int:
    [(unid_id,)] = h.consulta(bd, f"SELECT unid_id FROM sigat.unidad_medida WHERE unid_simbolo = '{simbolo}'")  # noqa: S608
    return int(str(unid_id))


def _aplicacion(h: SimpleNamespace, bd: str, **cambios: Any) -> dict[str, Any]:
    cuerpo = {
        "apli_registro_id": str(uuid4()),
        "lote_id": 12,
        "apli_producto_texto": "Cipermetrina",
        "apli_dosis": "2.0",
        "apli_dosis_uni_id": _unidad(h, bd, "mL/L"),
        "apli_area_tratada": "1.2",
        "apli_area_uni_id": _unidad(h, bd, "ha"),
        "apli_responsable_nombre": "Ana Productora",
        "t_observacion": AYER,
    }
    cuerpo.update(cambios)
    return cuerpo


def _cosecha(h: SimpleNamespace, bd: str, **cambios: Any) -> dict[str, Any]:
    cuerpo = {
        "cose_registro_id": str(uuid4()),
        "lote_id": 11,
        "cose_fecha_esperada": "2026-12-15",
        "cose_volumen_esperado": "500",
        "cose_volumen_uni_id": _unidad(h, bd, "kg"),
        "t_observacion": AYER,
    }
    cuerpo.update(cambios)
    return cuerpo


def _contar(h: SimpleNamespace, bd: str, tabla: str, columna: str, registro_id: str) -> int:
    [(n,)] = h.consulta(bd, f"SELECT count(*) FROM sigat.{tabla} WHERE {columna} = '{registro_id}'")  # noqa: S608
    return int(str(n))


def test_alta_de_aplicacion_crea_autorreporte_y_su_operacion(
    api: TestClient, bd: str, h: SimpleNamespace
) -> None:
    cuerpo = _aplicacion(h, bd)
    r = api.post(f"{P}/aplicaciones", headers=_ana(), json=cuerpo)

    assert r.status_code == 201, r.json()
    aplicacion = r.json()
    assert (aplicacion["apli_version"], aplicacion["linaje"], aplicacion["anulada"]) == (
        1,
        "autorreporte",
        False,
    )
    assert (aplicacion["producto"], aplicacion["dosis_unidad"], aplicacion["area_unidad"]) == (
        "Cipermetrina",
        "mL/L",
        "ha",
    )
    assert aplicacion["responsable"] == "Ana Productora"
    assert aplicacion["lote_descripcion"] == "Lote 2 · Centro"
    consulta = (
        "SELECT a.apli_linaje, a.usua_id, a.disp_id::text, o.oper_entidad, o.oper_accion, o.oper_clasificacion,"
        "       o.oper_version, o.disp_id::text, o.usua_id"
        "  FROM sigat.aplicacion_fitosanitaria a JOIN sigat.operacion_sync o ON o.oper_id = a.oper_id"
        " WHERE a.apli_registro_id = '{registro}'"
    )
    [fila] = h.consulta(bd, consulta.format(registro=cuerpo["apli_registro_id"]))
    assert fila == (
        "autorreporte",
        ANA,
        DISP_ANA,
        "aplicacion_fitosanitaria",
        "crear",
        "alta_nueva",
        1,
        DISP_ANA,
        ANA,
    )


def test_reenviar_la_misma_aplicacion_no_duplica(api: TestClient, bd: str, h: SimpleNamespace) -> None:
    cuerpo = _aplicacion(h, bd)
    primera = api.post(f"{P}/aplicaciones", headers=_ana(), json=cuerpo)
    segunda = api.post(f"{P}/aplicaciones", headers=_ana(), json=cuerpo)

    assert (primera.status_code, segunda.status_code) == (201, 201)
    assert primera.json()["apli_id"] == segunda.json()["apli_id"]
    registro = cuerpo["apli_registro_id"]
    assert _contar(h, bd, "aplicacion_fitosanitaria", "apli_registro_id", registro) == 1
    assert _contar(h, bd, "operacion_sync", "oper_registro_id", registro) == 1


def test_mismo_identificador_con_otro_contenido_es_409(api: TestClient, bd: str, h: SimpleNamespace) -> None:
    cuerpo = _aplicacion(h, bd)
    assert api.post(f"{P}/aplicaciones", headers=_ana(), json=cuerpo).status_code == 201

    r = api.post(f"{P}/aplicaciones", headers=_ana(), json={**cuerpo, "apli_dosis": "9"})

    assert (r.status_code, r.json()["codigo"]) == (409, "REGISTRO_EXISTENTE")


def test_lote_de_otro_productor_es_404_y_no_deja_rastro(api: TestClient, bd: str, h: SimpleNamespace) -> None:
    cuerpo = _aplicacion(h, bd, lote_id=21)
    r = api.post(f"{P}/aplicaciones", headers=_ana(), json=cuerpo)

    assert (r.status_code, r.json()["codigo"]) == (404, "LOTE_NO_ENCONTRADO")
    assert _contar(h, bd, "operacion_sync", "oper_registro_id", cuerpo["apli_registro_id"]) == 0


def test_solo_el_productor_registra_autorreportes(api: TestClient, bd: str, h: SimpleNamespace) -> None:
    tecnico = _token(TECNICO, RolCodigo.TECNICO, DISP_TECNICO)
    r = api.post(f"{P}/aplicaciones", headers=tecnico, json=_aplicacion(h, bd))

    assert (r.status_code, r.json()["codigo"]) == (403, "ROL_SIN_PERMISO")
    assert api.post(f"{P}/aplicaciones", json=_aplicacion(h, bd)).status_code == 401


@pytest.mark.parametrize(
    "cambios",
    [{"apli_producto_texto": None}, {"apli_dosis": "0"}, {"t_observacion": "2026-11-10T10:00:00"}],
)
def test_validacion_de_entrada_es_422(
    api: TestClient, bd: str, h: SimpleNamespace, cambios: dict[str, Any]
) -> None:
    r = api.post(f"{P}/aplicaciones", headers=_ana(), json=_aplicacion(h, bd, **cambios))

    assert (r.status_code, r.json()["codigo"]) == (422, "VALIDACION")


def test_fecha_futura_es_422(api: TestClient, bd: str, h: SimpleNamespace) -> None:
    futura = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    r = api.post(f"{P}/aplicaciones", headers=_ana(), json=_aplicacion(h, bd, t_observacion=futura))

    assert (r.status_code, r.json()["codigo"]) == (422, "FECHA_FUTURA")


def test_alta_de_cosecha_y_regla_p04(api: TestClient, bd: str, h: SimpleNamespace) -> None:
    abierta = _cosecha(h, bd)
    r = api.post(f"{P}/cosechas", headers=_ana(), json=abierta)
    assert r.status_code == 201, r.json()
    cosecha = r.json()
    assert (cosecha["cose_version"], cosecha["linaje"], cosecha["unidad"]) == (1, "autorreporte", "kg")
    assert cosecha["cose_fecha_real"] is None
    assert _contar(h, bd, "operacion_sync", "oper_registro_id", abierta["cose_registro_id"]) == 1

    otra_abierta = _cosecha(h, bd)
    r = api.post(f"{P}/cosechas", headers=_ana(), json=otra_abierta)
    assert (r.status_code, r.json()["codigo"]) == (409, "COSECHA_ABIERTA_EXISTENTE")
    assert _contar(h, bd, "cosecha", "cose_registro_id", otra_abierta["cose_registro_id"]) == 0
    assert _contar(h, bd, "operacion_sync", "oper_registro_id", otra_abierta["cose_registro_id"]) == 0

    cerrada = _cosecha(h, bd, cose_fecha_real="2026-11-15", cose_volumen_real="480")
    assert api.post(f"{P}/cosechas", headers=_ana(), json=cerrada).status_code == 201


def test_cosecha_con_datos_reales_incompletos_es_422(api: TestClient, bd: str, h: SimpleNamespace) -> None:
    r = api.post(
        f"{P}/cosechas", headers=_ana(), json=_cosecha(h, bd, lote_id=12, cose_fecha_real="2026-11-15")
    )

    assert (r.status_code, r.json()["codigo"]) == (422, "VALIDACION")
