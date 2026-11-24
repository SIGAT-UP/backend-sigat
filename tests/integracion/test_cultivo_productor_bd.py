"""PW01/PW02 — cultivo del productor y bloque ``productor`` del inicio contra PostgreSQL REAL.

Requiere ``SIGAT_DB_URL_PRUEBAS`` (ver ``conftest.py``). Usa una base TEMPORAL que se borra al final y
ejecuta el servicio con el repositorio real, en una transacción con ``sigat.usuario_actual`` = actor.

Escenario:

* Ana (productora, predio 1):
  - Lote 11 (Durazno): periodo de trampeo ABIERTO con MTD 9 / (5 × 5) = 0,36 (escenario Supresión);
    trampas vigentes 54125-R1-1, -3 y -5 (la -7 se retiró del lote); visita V1; aplicación A1 corregida
    (v2) y A2 anulada; cosecha ABIERTA esperada el 2026-11-15 con 850 kg.
  - Lote 12 (Durazno): periodo cerrado sin MTD; visita V2 (la más reciente de Ana); cosecha ya cerrada.
  - Lote 13: dado de baja -> nunca aparece.
  - Planificaciones: 2 pendientes y 1 aceptada dirigidas a ella.
* Bruno (productor, predio 2): lote 21 sin especie ni periodo, con visita, aplicación y planificación
  propias, POSTERIORES a las de Ana (no deben filtrarse a Ana).
* Carla: productora sin predios.
"""

import asyncio
from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import asyncpg
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from sigat_api.compartido.errores import NoImplementado
from sigat_api.compartido.tipos import Actor, Cliente, RolCodigo
from sigat_api.modules.concepto.repositorio import RepositorioConcepto
from sigat_api.modules.concepto.servicio import ServicioConcepto

pytestmark = pytest.mark.integracion

ANA = Actor(usua_id=2, rol=RolCodigo.PRODUCTOR, disp_id=None, cliente=Cliente.WEB)
BRUNO = Actor(usua_id=3, rol=RolCodigo.PRODUCTOR, disp_id=None, cliente=Cliente.WEB)
CARLA = Actor(usua_id=5, rol=RolCodigo.PRODUCTOR, disp_id=None, cliente=Cliente.WEB)

V1_FIN = datetime(2026, 3, 10, 15, 0, tzinfo=UTC)  # 2026-03-10 10:00 -05
V2_FIN = datetime(2026, 3, 15, 15, 0, tzinfo=UTC)
A1_OBS = datetime(2026, 3, 1, 13, 0, tzinfo=UTC)

DATOS = r"""
SET search_path = sigat, public;

INSERT INTO region (regi_id, regi_descripcion) VALUES (1, 'Región de prueba');
INSERT INTO departamento (depa_id, depa_descripcion, regi_id, depa_codigo) VALUES (1, 'Depto', 1, '99');
INSERT INTO municipio (muni_id, muni_descripcion, depa_id, muni_codigo) VALUES (1, 'Muni', 1, '001');
INSERT INTO centro_acopio (cent_id, cent_descripcion, depa_id) VALUES (1, 'Centro', 1);
INSERT INTO persona (pers_cc, pers_nombre, pers_apellido) VALUES
  (1001, 'Adela', 'Admin'), (1002, 'Tomás', 'Técnico'), (2001, 'Ana', 'Productora'),
  (2002, 'Bruno', 'Productor'), (2003, 'Carla', 'Productora'), (3001, 'Gloria', 'Agrónoma');
INSERT INTO administrador (admi_id, pers_cc, cent_id) VALUES (1, 1001, 1);
INSERT INTO tecnico (tecn_id, pers_cc, cent_id, admi_id, tecn_fecha_registro, esta_id)
  VALUES (1, 1002, 1, 1, DATE '2026-01-01', (SELECT esta_id FROM estado_registro WHERE esta_descripcion = 'activo'));
INSERT INTO productor (pers_cc, prod_fecha_registro, prod_tecnico_registro_id, muni_id) VALUES
  (2001, DATE '2026-01-01', 1, 1), (2002, DATE '2026-01-01', 1, 1), (2003, DATE '2026-01-01', 1, 1);
INSERT INTO usuario (usua_id, pers_cc, usua_usuario, usua_requiere_reinicio, rol_id, esta_id)
SELECT v.id, v.cc, v.usu, true, r.rol_id, e.esta_id
  FROM (VALUES (1, 1002::bigint, 'tecnico.prueba', 'TECNICO'),
               (2, 2001::bigint, 'ana.prueba', 'PRODUCTOR'),
               (3, 2002::bigint, 'bruno.prueba', 'PRODUCTOR'),
               (4, 3001::bigint, 'gloria.prueba', 'AGRONOMO_SUPERVISOR'),
               (5, 2003::bigint, 'carla.prueba', 'PRODUCTOR')) v(id, cc, usu, rol)
  JOIN rol r ON r.rol_codigo = v.rol
  JOIN estado_registro e ON e.esta_descripcion = 'activo';

INSERT INTO predio (pred_id, pred_nombre, muni_id, pred_area, pers_cc, pred_fecha_registro, pred_tecnico_registro_id)
  VALUES (1, 'Predio Ana', 1, 10, 2001, DATE '2026-01-01', 1), (2, 'Predio Bruno', 1, 10, 2002, DATE '2026-01-01', 1);
INSERT INTO lote (lote_id, lote_codigo, lote_descripcion, lote_area, pred_id, espc_id, lote_fecha_registro,
                  lote_tecnico_registro_id, lote_fecha_baja) VALUES
  (11, 'L11', 'Lote 1 · Norte', 2, 1, (SELECT espc_id FROM especie_cultivo WHERE espc_descripcion = 'Durazno'),
   DATE '2026-01-01', 1, NULL),
  (12, 'L12', 'Lote 2 · Centro', 2, 1, (SELECT espc_id FROM especie_cultivo WHERE espc_descripcion = 'Durazno'),
   DATE '2026-01-01', 1, NULL),
  (13, 'L13', 'Lote 3 · Retirado', 2, 1, NULL, DATE '2026-01-01', 1, DATE '2026-02-01'),
  (21, 'L21', 'Lote único', 2, 2, NULL, DATE '2026-01-01', 1, NULL);

INSERT INTO vigilancia (vigi_id, vigi_descripcion) VALUES (1, 'Vigilancia de prueba');
INSERT INTO trampa (tram_id, tram_codigo, tipt_id, atra_id, esta_id, tram_fecha_registro, tram_tecnico_registro_id)
SELECT v.id, v.cod, t.tipt_id, (SELECT min(atra_id) FROM atrayente), e.esta_id, DATE '2026-01-01', 1
  FROM (VALUES (1, '54125-R1-1'), (2, '54125-R1-3'), (3, '54125-R1-5'), (4, '54125-R1-7'), (5, '54125-R1-9')) v(id, cod)
  JOIN tipo_trampa t ON t.tipt_descripcion = 'Jackson'
  JOIN estado_registro e ON e.esta_descripcion = 'activo';
INSERT INTO ubicacion_trampa (ubic_id, tram_id, pred_id, lote_id, ubic_fecha, ubic_fecha_fin, tecn_id, vigi_id, ubic_long, ubic_lat) VALUES
  (1, 3, 1, 11, DATE '2026-01-01', NULL,              1, 1, -72.5, 7.9),
  (2, 1, 1, 11, DATE '2026-01-01', NULL,              1, 1, -72.5, 7.9),
  (3, 2, 1, 11, DATE '2026-01-01', NULL,              1, 1, -72.5, 7.9),
  (4, 4, 1, 11, DATE '2026-01-01', DATE '2026-03-01', 1, 1, -72.5, 7.9),
  (5, 5, 2, 21, DATE '2026-01-01', NULL,              1, 1, -72.5, 7.9);

INSERT INTO programa_inspeccion (prog_id, pred_id, prog_version, prog_vigente_desde, prog_periodo_lectura_dias,
                                 prog_distancia_min_trampas_m)
  VALUES (1, 1, 1, DATE '2026-01-01', 7, 50);
INSERT INTO periodo_trampeo (peri_id, lote_id, vigi_id, prog_id, peri_inicio, peri_fin, peri_estado) VALUES
  (1, 11, 1, 1, DATE '2026-03-08', DATE '2026-03-14', 'abierto'),
  (2, 12, 1, 1, DATE '2026-03-01', DATE '2026-03-07', 'cerrado');
INSERT INTO indice_mtd (indi_id, peri_id, indi_version, indi_moscas, indi_trampas, indi_dias_exposicion,
                        indi_umbral_aplicado, norm_id, indi_resultado_contraste, esce_id, indi_calculado_en) VALUES
  (101, 1, 1, 9, 5, 5, NULL, NULL, 'sin_umbral',
   (SELECT esce_id FROM escenario_trampeo WHERE esce_descripcion = 'Supresión'), '2026-03-14 09:00-05');

INSERT INTO dispositivo (disp_id, disp_plataforma) VALUES ('00000000-0000-0000-0000-0000000000d1', 'android');
CREATE FUNCTION pg_temp.op(p_entidad text, p_usua integer, p_registro uuid, p_version integer) RETURNS bigint
LANGUAGE sql AS $$
  INSERT INTO sigat.operacion_sync (disp_id, oper_cliente_id, usua_id, oper_entidad, oper_accion, oper_registro_id,
                                    oper_version, oper_hash_contenido, oper_clasificacion, oper_t_captura)
  VALUES ('00000000-0000-0000-0000-0000000000d1', gen_random_uuid(), p_usua, p_entidad,
          CASE WHEN p_version = 1 THEN 'crear' ELSE 'corregir' END, p_registro, p_version,
          md5(random()::text) || md5(random()::text),
          CASE WHEN p_version = 1 THEN 'alta_nueva' ELSE 'correccion' END, TIMESTAMPTZ '2026-03-10 12:00-05')
  RETURNING oper_id $$;

INSERT INTO visita (visi_id, disp_id, oper_id, usua_id, pred_id, visi_t_inicio_obs, visi_t_fin_obs, visi_t_captura) VALUES
  ('00000000-0000-0000-0000-00000000b001', '00000000-0000-0000-0000-0000000000d1',
   pg_temp.op('visita', 1, '00000000-0000-0000-0000-00000000b001', 1), 1, 1,
   '2026-03-10 09:00-05', '2026-03-10 10:00-05', '2026-03-10 10:05-05'),
  ('00000000-0000-0000-0000-00000000b002', '00000000-0000-0000-0000-0000000000d1',
   pg_temp.op('visita', 1, '00000000-0000-0000-0000-00000000b002', 1), 1, 1,
   '2026-03-15 09:00-05', '2026-03-15 10:00-05', '2026-03-15 10:05-05'),
  ('00000000-0000-0000-0000-00000000b003', '00000000-0000-0000-0000-0000000000d1',
   pg_temp.op('visita', 1, '00000000-0000-0000-0000-00000000b003', 1), 1, 2,
   '2026-03-20 09:00-05', '2026-03-20 10:00-05', '2026-03-20 10:05-05');
INSERT INTO visita_lote (visi_id, lote_id, pred_id) VALUES
  ('00000000-0000-0000-0000-00000000b001', 11, 1),
  ('00000000-0000-0000-0000-00000000b002', 12, 1),
  ('00000000-0000-0000-0000-00000000b003', 21, 2);

INSERT INTO producto_fitosanitario (prof_id, prof_nombre) VALUES (1, 'Cipermetrina');
INSERT INTO aplicacion_fitosanitaria (apli_registro_id, apli_version, lote_id, prof_id, apli_producto_texto, apli_dosis,
                                      apli_dosis_uni_id, apli_area_tratada, apli_area_uni_id, pers_cc_responsable,
                                      usua_id, disp_id, oper_id, apli_t_observacion, apli_t_captura,
                                      apli_anulada, apli_motivo_anulacion)
SELECT v.reg::uuid, v.ver, v.lote, 1, NULL, 2.0, (SELECT unid_id FROM unidad_medida WHERE unid_simbolo = 'mL/L'),
       1.2, (SELECT unid_id FROM unidad_medida WHERE unid_simbolo = 'ha'), v.resp, v.usua,
       '00000000-0000-0000-0000-0000000000d1', pg_temp.op('aplicacion_fitosanitaria', v.usua, v.reg::uuid, v.ver),
       v.obs::timestamptz, v.obs::timestamptz + interval '1 hour', v.anulada, v.motivo
  FROM (VALUES
    (1, '00000000-0000-0000-0000-00000000e001', 1, 11, 2001::bigint, 2, '2026-03-01 08:00-05', false, NULL),
    (2, '00000000-0000-0000-0000-00000000e001', 2, 11, 2001::bigint, 2, '2026-03-01 08:00-05', false, NULL),
    (3, '00000000-0000-0000-0000-00000000e002', 1, 11, 2001::bigint, 2, '2026-03-05 08:00-05', false, NULL),
    (4, '00000000-0000-0000-0000-00000000e002', 2, 11, 2001::bigint, 2, '2026-03-05 08:00-05', true, 'Registro equivocado'),
    (5, '00000000-0000-0000-0000-00000000e003', 1, 21, 2002::bigint, 3, '2026-03-25 08:00-05', false, NULL)
  ) v(orden, reg, ver, lote, resp, usua, obs, anulada, motivo)
 ORDER BY v.orden;

INSERT INTO cosecha (cose_registro_id, cose_version, lote_id, cose_fecha_esperada, cose_volumen_esperado, cose_fecha_real,
                     cose_volumen_real, cose_volumen_uni_id, usua_id, disp_id, oper_id, cose_t_observacion, cose_t_captura)
SELECT v.reg::uuid, 1, v.lote, v.esperada::date, v.volumen, v.real_f::date, v.real_v,
       (SELECT unid_id FROM unidad_medida WHERE unid_simbolo = 'kg'), 2, '00000000-0000-0000-0000-0000000000d1',
       pg_temp.op('cosecha', 2, v.reg::uuid, 1), TIMESTAMPTZ '2026-03-02 08:00-05', TIMESTAMPTZ '2026-03-02 08:05-05'
  FROM (VALUES ('00000000-0000-0000-0000-00000000f001', 11, '2026-11-15', 850::numeric, NULL, NULL::numeric),
               ('00000000-0000-0000-0000-00000000f002', 12, '2026-02-20', 300::numeric, '2026-02-22', 280::numeric)
  ) v(reg, lote, esperada, volumen, real_f, real_v);

-- Solo para contar planificaciones por estado y destinatario: se cargan sin disparadores (los avisos y
-- validaciones de planificación no son objeto de esta prueba).
SET session_replication_role = replica;
INSERT INTO planificacion (plan_id, usua_id_destinatario, usua_id_creador, plan_actividad, plan_fecha_inicio,
                           plan_estado, plan_observacion_respuesta, plan_respondida_en, usua_id_respuesta) VALUES
  ('00000000-0000-0000-0000-0000000000a1', 2, 4, 'Muestreo', DATE '2026-03-01', 'pendiente', NULL, NULL, NULL),
  ('00000000-0000-0000-0000-0000000000a2', 2, 4, 'Poda', DATE '2026-03-02', 'pendiente', NULL, NULL, NULL),
  ('00000000-0000-0000-0000-0000000000a3', 2, 4, 'Riego', DATE '2026-03-03', 'aceptada', 'Listo',
   TIMESTAMPTZ '2026-03-04 10:00+00', 2),
  ('00000000-0000-0000-0000-0000000000a4', 3, 4, 'Fumigación', DATE '2026-03-03', 'pendiente', NULL, NULL, NULL);
SET session_replication_role = DEFAULT;
"""


def _dsn(h: SimpleNamespace, nombre: str) -> str:
    return str(h.url(nombre)).replace("postgresql+asyncpg://", "postgresql://", 1)


@pytest.fixture(scope="module")
def bd(h: SimpleNamespace) -> Iterator[str]:
    nombre = h.crear_bd()
    try:
        r = h.alembic(nombre, "upgrade", "head")
        assert r.returncode == 0, r.stderr

        async def _cargar() -> None:
            con = await asyncpg.connect(_dsn(h, nombre))
            try:
                async with con.transaction():
                    await con.execute(DATOS)
            finally:
                await con.close()

        asyncio.run(_cargar())
        yield nombre
    finally:
        h.borrar_bd(nombre)


def consulta(h: SimpleNamespace, bd: str, actor: Actor, metodo: str) -> Any:
    """Una transacción por llamada con ``sigat.usuario_actual`` = actor, como ``api.dependencias.conexion``."""

    async def _correr() -> Any:
        motor = create_async_engine(h.url(bd))
        try:
            async with motor.begin() as con:
                await con.execute(
                    text("SELECT set_config('sigat.usuario_actual', CAST(:u AS text), true)"),
                    {"u": str(actor.usua_id)},
                )
                return await getattr(ServicioConcepto(RepositorioConcepto(con), "America/Bogota"), metodo)(
                    actor
                )
        finally:
            await motor.dispose()

    return asyncio.run(_correr())


# ------------------------------------------------------------------ cultivo (datos ya implementados)
def test_cultivo_de_ana_con_datos_reales(h: SimpleNamespace, bd: str) -> None:
    datos = consulta(h, bd, ANA, "datos_cultivo")
    assert [lote.lote_id for lote in datos.lotes] == [11, 12]  # sin el lote dado de baja ni el de Bruno
    assert datos.cultivo == "Durazno"
    assert datos.vigilancia_activa is True  # el lote 11 tiene un periodo abierto
    assert datos.ultima_visita == V2_FIN
    assert datos.ultima_aplicacion == A1_OBS  # la A2 anulada no cuenta; la de Bruno (posterior) tampoco

    lote11, lote12 = datos.lotes
    assert lote11.lote_descripcion == "Lote 1 · Norte"
    assert lote11.mtd == Decimal("0.360000")  # indice_mtd.indi_valor, calculado por la BD
    assert lote11.rango_trampas == "54125-R1-1 a 54125-R1-5"  # solo las vigentes, por número
    assert lote11.ultima_visita == V1_FIN
    assert lote11.ultima_aplicacion == A1_OBS
    assert (lote11.cosecha_esperada, lote11.volumen_esperado) == (date(2026, 11, 15), Decimal("850.000"))
    assert lote11.concepto is None  # sin concepto emitido: no se inventa

    assert lote12.mtd is None  # periodo sin índice MTD
    assert lote12.rango_trampas is None
    assert lote12.ultima_visita == V2_FIN
    assert lote12.ultima_aplicacion is None
    assert (lote12.cosecha_esperada, lote12.volumen_esperado) == (None, None)  # su cosecha ya se cerró


def test_cultivo_de_bruno_no_ve_lotes_de_ana(h: SimpleNamespace, bd: str) -> None:
    datos = consulta(h, bd, BRUNO, "datos_cultivo")
    assert [lote.lote_id for lote in datos.lotes] == [21]
    assert datos.cultivo is None  # su lote no tiene especie registrada
    assert datos.vigilancia_activa is False
    assert datos.lotes[0].rango_trampas == "54125-R1-9"
    assert datos.lotes[0].mtd is None


def test_productora_sin_lotes(h: SimpleNamespace, bd: str) -> None:
    datos = consulta(h, bd, CARLA, "datos_cultivo")
    assert (datos.lotes, datos.cultivo, datos.vigilancia_activa) == ([], None, False)
    assert (datos.ultima_visita, datos.ultima_aplicacion) == (None, None)


def test_cultivo_productor_sigue_respondiendo_501(h: SimpleNamespace, bd: str) -> None:
    with pytest.raises(NoImplementado, match="lotes_revisados"):
        consulta(h, bd, ANA, "cultivo_productor")


# ------------------------------------------------------------------ inicio del productor
def test_inicio_de_ana(h: SimpleNamespace, bd: str) -> None:
    inicio = consulta(h, bd, ANA, "inicio_productor")
    assert (inicio.lotes, inicio.planificaciones_por_responder, inicio.ultima_visita) == (2, 2, V2_FIN)


def test_inicio_de_bruno_y_de_carla(h: SimpleNamespace, bd: str) -> None:
    bruno = consulta(h, bd, BRUNO, "inicio_productor")
    assert (bruno.lotes, bruno.planificaciones_por_responder) == (1, 1)
    assert bruno.ultima_visita == datetime(2026, 3, 20, 15, 0, tzinfo=UTC)
    carla = consulta(h, bd, CARLA, "inicio_productor")
    assert (carla.lotes, carla.planificaciones_por_responder, carla.ultima_visita) == (0, 0, None)
