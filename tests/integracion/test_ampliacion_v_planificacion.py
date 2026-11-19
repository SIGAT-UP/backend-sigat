"""``v_planificacion`` ampliada (migración 0010) contra PostgreSQL REAL.

Requiere ``SIGAT_DB_URL_PRUEBAS`` (ver ``conftest.py``). Usa bases TEMPORALES que se borran al final.

Los datos se cargan con los disparadores desactivados (``session_replication_role = replica``): la
prueba es de una vista de solo lectura y las validaciones de planificación tienen sus propias pruebas.
Los CHECK de la tabla siguen activos (p. ej. el rechazo exige observación).
"""

import asyncio
from collections.abc import Iterator
from types import SimpleNamespace

import asyncpg
import pytest

pytestmark = pytest.mark.integracion

PENDIENTE = "00000000-0000-0000-0000-0000000000a1"
RECHAZADA = "00000000-0000-0000-0000-0000000000a2"
ACEPTADA = "00000000-0000-0000-0000-0000000000a3"
DOCUMENTO = "00000000-0000-0000-0000-0000000000f1"

DATOS = r"""
SET search_path = sigat, public;
SET session_replication_role = replica;

INSERT INTO region (regi_id, regi_descripcion) VALUES (1, 'Región de prueba');
INSERT INTO departamento (depa_id, depa_descripcion, regi_id, depa_codigo) VALUES (1, 'Depto', 1, '99');
INSERT INTO municipio (muni_id, muni_descripcion, depa_id, muni_codigo) VALUES (1, 'Muni', 1, '001');
INSERT INTO persona (pers_cc, pers_nombre, pers_apellido) VALUES (3001, 'Gloria', 'Agrónoma'), (2001, 'Ana', 'Productora');
INSERT INTO usuario (usua_id, pers_cc, usua_usuario, usua_requiere_reinicio, rol_id, esta_id)
SELECT v.id, v.cc, v.usu, true, r.rol_id, e.esta_id
  FROM (VALUES (1, 3001::bigint, 'gloria.prueba', 'AGRONOMO_SUPERVISOR'),
               (2, 2001::bigint, 'ana.prueba', 'PRODUCTOR')) v(id, cc, usu, rol)
  JOIN rol r ON r.rol_codigo = v.rol
  JOIN estado_registro e ON e.esta_descripcion = 'activo';
INSERT INTO predio (pred_id, pred_nombre, muni_id, pred_area, pers_cc, pred_fecha_registro, pred_tecnico_registro_id)
  VALUES (1, 'Predio Ana', 1, 10, 2001, DATE '2026-01-01', 1);
INSERT INTO lote (lote_id, lote_codigo, lote_descripcion, lote_area, pred_id, lote_fecha_registro, lote_tecnico_registro_id) VALUES
  (11, 'L11', 'Lote 1 · Norte', 2, 1, DATE '2026-01-01', 1),
  (12, 'L12', 'Lote 2 · Centro', 2, 1, DATE '2026-01-01', 1);

INSERT INTO archivo_adjunto (arch_id, arch_clase, arch_nombre_original, arch_mime, arch_tamano_bytes, arch_hash_sha256, arch_paginas)
  VALUES ('00000000-0000-0000-0000-0000000000f1', 'documento_instruccion', 'instrucciones.pdf', 'application/pdf', 2048, repeat('a', 64), 3);

INSERT INTO planificacion (plan_id, usua_id_destinatario, usua_id_creador, plan_actividad, plan_fecha_inicio,
                           arch_id_documento, plan_documento_clase, plan_estado, plan_observacion_respuesta,
                           plan_respondida_en, usua_id_respuesta) VALUES
  ('00000000-0000-0000-0000-0000000000a1', 2, 1, 'Muestreo', DATE '2026-03-01', NULL, NULL, 'pendiente', NULL, NULL, NULL),
  ('00000000-0000-0000-0000-0000000000a2', 2, 1, 'Poda', DATE '2026-03-01', '00000000-0000-0000-0000-0000000000f1',
   'documento_instruccion', 'rechazada', 'El lote está en cosecha', TIMESTAMPTZ '2026-03-02 10:00+00', 2),
  ('00000000-0000-0000-0000-0000000000a3', 2, 1, 'Riego', DATE '2026-03-01', NULL, NULL, 'aceptada',
   'Llegaré temprano', TIMESTAMPTZ '2026-03-02 10:00+00', 2);
INSERT INTO planificacion_lote (plan_id, lote_id) VALUES
  ('00000000-0000-0000-0000-0000000000a2', 12), ('00000000-0000-0000-0000-0000000000a2', 11);

SET session_replication_role = DEFAULT;
"""

COLUMNAS_ANTERIORES = [
    "plan_id", "plan_actividad", "plan_fecha_inicio", "plan_fecha_fin", "plan_hora_desde", "plan_hora_hasta",
    "plan_estado", "plan_observaciones", "plan_observacion_respuesta", "plan_creada_en", "plan_respondida_en",
    "usua_id_destinatario", "destinatario", "rol_destinatario", "usua_id_creador", "creador", "documento",
    "lotes", "plan_id_origen", "usua_id_respuesta", "respondio", "lotes_pendientes", "lotes_ejecutados",
    "lotes_no_ejecutados",
]  # fmt: skip
COLUMNAS_NUEVAS = [
    ("arch_id_documento", "uuid"),
    ("plan_documento_clase", "character varying"),
    ("documento_mime", "character varying"),
    ("documento_bytes", "bigint"),
    ("documento_paginas", "smallint"),
    ("lotes_descripcion", "ARRAY"),
    ("plan_motivo_rechazo", "character varying"),
]
COLUMNAS_VISTA = (
    "SELECT column_name, data_type FROM information_schema.columns"
    " WHERE table_schema = 'sigat' AND table_name = 'v_planificacion' ORDER BY ordinal_position"
)


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


def _fila(h: SimpleNamespace, bd: str, plan_id: str, columnas: str) -> tuple[object, ...]:
    [fila] = h.consulta(bd, f"SELECT {columnas} FROM sigat.v_planificacion WHERE plan_id = '{plan_id}'")  # noqa: S608
    return fila


def test_conserva_las_columnas_y_agrega_las_de_et_al_final(bd: str, h: SimpleNamespace) -> None:
    columnas = h.consulta(bd, COLUMNAS_VISTA)
    assert [c for c, _ in columnas[: len(COLUMNAS_ANTERIORES)]] == COLUMNAS_ANTERIORES
    assert columnas[len(COLUMNAS_ANTERIORES) :] == COLUMNAS_NUEVAS


def test_motivo_de_rechazo_solo_en_planificaciones_rechazadas(bd: str, h: SimpleNamespace) -> None:
    columnas = "plan_estado, plan_observacion_respuesta, plan_motivo_rechazo"
    assert _fila(h, bd, RECHAZADA, columnas) == (
        "rechazada",
        "El lote está en cosecha",
        "El lote está en cosecha",
    )
    assert _fila(h, bd, ACEPTADA, columnas) == ("aceptada", "Llegaré temprano", None)
    assert _fila(h, bd, PENDIENTE, columnas) == ("pendiente", None, None)


def test_datos_del_documento(bd: str, h: SimpleNamespace) -> None:
    columnas = "documento, arch_id_documento::text, plan_documento_clase, documento_mime, documento_bytes, documento_paginas"
    assert _fila(h, bd, RECHAZADA, columnas) == (
        "instrucciones.pdf", DOCUMENTO, "documento_instruccion", "application/pdf", 2048, 3,
    )  # fmt: skip
    assert _fila(h, bd, PENDIENTE, columnas) == (None, None, None, None, None, None)


def test_descripciones_de_lotes_en_el_mismo_orden_que_los_codigos(bd: str, h: SimpleNamespace) -> None:
    assert _fila(h, bd, RECHAZADA, "lotes, lotes_descripcion") == (
        ["L11", "L12"],
        ["Lote 1 · Norte", "Lote 2 · Centro"],
    )
    assert _fila(h, bd, PENDIENTE, "lotes, lotes_descripcion") == ([], [])


def test_las_consultas_existentes_siguen_funcionando(bd: str, h: SimpleNamespace) -> None:
    """Las columnas anteriores conservan nombre y contenido para quien ya las lee (p. ej. la PR #24)."""
    filas = h.consulta(bd, f"SELECT {', '.join(COLUMNAS_ANTERIORES)} FROM sigat.v_planificacion")  # noqa: S608
    assert len(filas) == 3
    assert _fila(h, bd, RECHAZADA, "destinatario, creador, respondio, lotes_pendientes") == (
        "Ana Productora", "Gloria Agrónoma", "Ana Productora", 2,
    )  # fmt: skip


def test_downgrade_restaura_la_vista_anterior_y_reaplicar_la_amplia(h: SimpleNamespace) -> None:
    nombre = h.crear_bd()
    try:
        assert h.alembic(nombre, "upgrade", "head").returncode == 0
        ampliada = h.consulta(nombre, COLUMNAS_VISTA)
        r = h.alembic(nombre, "downgrade", "0009")
        assert r.returncode == 0, r.stderr
        anterior = h.consulta(nombre, COLUMNAS_VISTA)
        assert [c for c, _ in anterior] == COLUMNAS_ANTERIORES
        assert ampliada[: len(anterior)] == anterior
        assert h.alembic(nombre, "upgrade", "head").returncode == 0
        assert h.consulta(nombre, COLUMNAS_VISTA) == ampliada
    finally:
        h.borrar_bd(nombre)
