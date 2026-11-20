"""``v_notificacion_app`` (migración 0009) y la bandeja que la consume, contra PostgreSQL REAL.

Requiere ``SIGAT_DB_URL_PRUEBAS`` (ver ``conftest.py``). Usa bases TEMPORALES que se borran al final.
Datos: Ana tiene un aviso leído y uno sin leer; Bruno no tiene avisos.
"""

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import asyncpg
import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from sigat_api.modules.notificaciones.repositorio import RepositorioNotificaciones

pytestmark = pytest.mark.integracion

RAIZ = Path(__file__).resolve().parents[2]
ARCHIVO_SQL = RAIZ / "bd" / "sql" / "18_vista_notificacion_app.sql"

ANA, BRUNO = 2, 3
AVISO_LEIDO, AVISO_PENDIENTE = 101, 102

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

INSERT INTO notificacion (noti_id, usua_id, cate_id, noti_titulo, noti_cuerpo, noti_evento_clave,
                          noti_destino_ruta, noti_destino_argumento, noti_creada_en, noti_leida_en)
SELECT v.id, 2, c.cate_id, v.titulo, 'Cuerpo', v.clave, v.ruta, v.arg, v.creada, v.leida
  FROM (VALUES (101, 'Aviso leído', 'evento-1', NULL, NULL,
                TIMESTAMPTZ '2026-03-01 10:00+00', TIMESTAMPTZ '2026-03-02 10:00+00'),
               (102, 'Aviso pendiente', 'evento-2', '/productor/planeaciones', '7',
                TIMESTAMPTZ '2026-03-03 10:00+00', NULL::timestamptz)) v(id, titulo, clave, ruta, arg, creada, leida)
  JOIN categoria_notificacion c ON c.cate_codigo = 'asignacion';
"""

COLUMNAS = [
    ("noti_id", "bigint"),
    ("usua_id", "integer"),
    ("noti_titulo", "character varying"),
    ("noti_cuerpo", "text"),
    ("noti_destino_ruta", "character varying"),
    ("noti_destino_argumento", "character varying"),
    ("noti_creada_en", "timestamp with time zone"),
    ("noti_leida_en", "timestamp with time zone"),
    ("cate_codigo", "character varying"),
    ("cate_descripcion", "character varying"),
    ("no_leida", "boolean"),
]


def _dsn(h: SimpleNamespace, nombre: str) -> str:
    return str(h.url(nombre)).replace("postgresql+asyncpg://", "postgresql://", 1)


def _ejecutar(h: SimpleNamespace, nombre: str, sql: str) -> None:
    async def _correr() -> None:
        con = await asyncpg.connect(_dsn(h, nombre))
        try:
            await con.execute(sql)
        finally:
            await con.close()

    asyncio.run(_correr())


def _con_repositorio(h: SimpleNamespace, nombre: str, uso: Any) -> Any:
    """Ejecuta ``uso(repo)`` en una transacción que se revierte: las pruebas no dejan cambios."""

    async def _correr() -> Any:
        motor = create_async_engine(h.url(nombre))
        try:
            async with motor.connect() as con:
                resultado = await uso(RepositorioNotificaciones(con))
                await con.rollback()
                return resultado
        finally:
            await motor.dispose()

    return asyncio.run(_correr())


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


def test_columnas_y_tipos_de_et_3_2_7(bd: str, h: SimpleNamespace) -> None:
    columnas = h.consulta(
        bd,
        "SELECT column_name, data_type FROM information_schema.columns"
        " WHERE table_schema = 'sigat' AND table_name = 'v_notificacion_app' ORDER BY ordinal_position",
    )
    assert columnas == COLUMNAS


def test_no_leida_y_categoria(bd: str, h: SimpleNamespace) -> None:
    filas = h.consulta(
        bd,
        "SELECT noti_id, usua_id, cate_codigo, no_leida, noti_destino_ruta, noti_destino_argumento"
        " FROM sigat.v_notificacion_app ORDER BY noti_id",
    )
    assert filas == [
        (AVISO_LEIDO, ANA, "asignacion", False, None, None),
        (AVISO_PENDIENTE, ANA, "asignacion", True, "/productor/planeaciones", "7"),
    ]


def test_un_aviso_por_fila_de_notificacion(bd: str, h: SimpleNamespace) -> None:
    assert h.consulta(bd, "SELECT count(*) FROM sigat.v_notificacion_app") == h.consulta(
        bd, "SELECT count(*) FROM sigat.notificacion"
    )


def test_la_bandeja_solo_devuelve_los_no_leidos_del_usuario(bd: str, h: SimpleNamespace) -> None:
    async def uso(repo: RepositorioNotificaciones) -> dict[str, Any]:
        return {
            "ana": [f["noti_id"] for f in await repo.listar(ANA, None, 50)],
            "bruno": await repo.listar(BRUNO, None, 50),
            "conteo_ana": await repo.conteo_no_leidas(ANA),
            "conteo_bruno": await repo.conteo_no_leidas(BRUNO),
        }

    assert _con_repositorio(h, bd, uso) == {
        "ana": [AVISO_PENDIENTE],
        "bruno": [],
        "conteo_ana": 1,
        "conteo_bruno": 0,
    }


def test_paginacion_estable_con_empates_y_avisos_leidos_entre_paginas(bd: str, h: SimpleNamespace) -> None:
    """Los avisos creados en una misma transacción comparten noti_creada_en: desempata noti_id."""

    async def uso(repo: RepositorioNotificaciones) -> dict[str, Any]:
        for i in range(5):
            await repo.crear(BRUNO, "avisos_predio", f"Aviso {i}", "Cuerpo", f"prueba-{i}", None, None)
        vistos: list[int] = []
        primera = await repo.listar(BRUNO, None, 2)
        vistos += [f["noti_id"] for f in primera]
        for f in primera:
            await repo.marcar_leida(BRUNO, int(f["noti_id"]), datetime.now(UTC))
        despues = (primera[-1]["noti_creada_en"], int(primera[-1]["noti_id"]))
        resto = await repo.listar(BRUNO, despues, 50)
        vistos += [f["noti_id"] for f in resto]
        return {"vistos": vistos, "bandeja": [f["noti_id"] for f in await repo.listar(BRUNO, None, 50)]}

    resultado = _con_repositorio(h, bd, uso)
    assert len(resultado["vistos"]) == 5
    assert resultado["vistos"] == sorted(resultado["vistos"], reverse=True)
    assert resultado["bandeja"] == resultado["vistos"][2:]


def test_marcar_leido_saca_el_aviso_de_la_bandeja_sin_borrarlo(bd: str, h: SimpleNamespace) -> None:
    async def uso(repo: RepositorioNotificaciones) -> dict[str, Any]:
        marcado = await repo.marcar_leida(ANA, AVISO_PENDIENTE, datetime.now(UTC))
        return {"marcado": marcado, "bandeja": await repo.listar(ANA, None, 50)}

    assert _con_repositorio(h, bd, uso) == {"marcado": True, "bandeja": []}
    assert h.consulta(bd, "SELECT count(*) FROM sigat.notificacion WHERE usua_id = 2") == [(2,)]


def test_las_columnas_de_la_bandeja_conservan_su_forma(bd: str, h: SimpleNamespace) -> None:
    async def uso(repo: RepositorioNotificaciones) -> dict[str, Any]:
        [fila] = await repo.listar(ANA, None, 50)
        return fila

    assert _con_repositorio(h, bd, uso) == {
        "noti_id": AVISO_PENDIENTE,
        "cate_codigo": "asignacion",
        "noti_titulo": "Aviso pendiente",
        "noti_cuerpo": "Cuerpo",
        "noti_creada_en": datetime(2026, 3, 3, 10, tzinfo=UTC),
        "noti_leida_en": None,
        "noti_destino_ruta": "/productor/planeaciones",
        "noti_destino_argumento": "7",
    }


def test_un_usuario_no_marca_avisos_ajenos(bd: str, h: SimpleNamespace) -> None:
    async def uso(repo: RepositorioNotificaciones) -> bool:
        return await repo.marcar_leida(BRUNO, AVISO_PENDIENTE, datetime.now(UTC))

    assert _con_repositorio(h, bd, uso) is False
    no_leida = dict(h.consulta(bd, "SELECT noti_id, no_leida FROM sigat.v_notificacion_app"))
    assert no_leida[AVISO_PENDIENTE] is True


def test_reaplicar_el_sql_es_idempotente(bd: str, h: SimpleNamespace) -> None:
    _ejecutar(h, bd, ARCHIVO_SQL.read_text(encoding="utf-8"))
    test_columnas_y_tipos_de_et_3_2_7(bd, h)
