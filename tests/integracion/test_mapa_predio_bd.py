"""GET /predios/{pred_id}/mapa contra PostgreSQL/PostGIS REAL (solo validación: no cambia la implementación).

Requiere ``SIGAT_DB_URL_PRUEBAS`` (ver ``conftest.py``). Usa una base TEMPORAL que se borra al final y
ejecuta ``ServicioPredios.mapa`` con el repositorio real, en una transacción con ``sigat.usuario_actual``.

Geometrías controladas en EPSG:4326 (lon, lat), cargadas con las validaciones de la BD activas
(``ST_IsValid``, RF-084: el lote dentro del predio, vigencias sin solape):

* Predio 1 (Ana): cuadrado lon [-72.50, -72.49] × lat [7.90, 7.91].
  - Lote 11: v1 vigente desde 2026-01-01.
  - Lote 12: v1 hasta 2026-03-01 y v2 desde 2026-03-01 (otra forma) -> el mapa elige la vigente en ``instante``.
  - Lote 13: dado de baja (tiene geometría) -> no aparece.
  - Retícula de 100 m con una celda. Trampas: T1 en el lote 11 (vigente) y T2 retirada.
* Predio 2 (Bruno): sin geometría; lote 21 sin geometría y sin trampas.
"""

import asyncio
import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import asyncpg
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from sigat_api.compartido.errores import NoEncontrado
from sigat_api.compartido.tipos import Actor, Cliente, RolCodigo
from sigat_api.modules.configuracion.esquemas import MapaPredio
from sigat_api.modules.configuracion.repositorio import RepositorioConfiguracion
from sigat_api.modules.configuracion.servicio import ServicioPredios

pytestmark = pytest.mark.integracion

RAIZ = Path(__file__).resolve().parents[2]
ANA = Actor(usua_id=2, rol=RolCodigo.PRODUCTOR, disp_id=None, cliente=Cliente.WEB)
BRUNO = Actor(usua_id=3, rol=RolCodigo.PRODUCTOR, disp_id=None, cliente=Cliente.WEB)

T1 = (-72.497, 7.903)

DATOS = """
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

INSERT INTO predio (pred_id, pred_nombre, pred_codigo, muni_id, pred_area, pers_cc, pred_fecha_registro,
                    pred_tecnico_registro_id, pred_geom) VALUES
  (1, 'Predio Ana', 'P-001', 1, 10, 2001, DATE '2026-01-01', 1, ST_GeomFromText('MULTIPOLYGON(((-72.50 7.90, -72.49 7.90, -72.49 7.91, -72.50 7.91, -72.50 7.90)))', 4326)),
  (2, 'Predio Bruno', NULL, 1, 10, 2002, DATE '2026-01-01', 1, NULL);
INSERT INTO lote (lote_id, lote_codigo, lote_descripcion, lote_area, pred_id, lote_fecha_registro,
                  lote_tecnico_registro_id, lote_fecha_baja) VALUES
  (11, 'L11', 'Lote 1 · Norte', 2, 1, DATE '2026-01-01', 1, NULL),
  (12, 'L12', 'Lote 2 · Centro', 1.5, 1, DATE '2026-01-01', 1, NULL),
  (13, 'L13', 'Lote 3 · Retirado', 1, 1, DATE '2026-01-01', 1, DATE '2026-02-01'),
  (21, 'L21', 'Lote único', 2, 2, DATE '2026-01-01', 1, NULL);
INSERT INTO lote_geometria (lote_id, lotg_version, lotg_geom, lotg_vigente_desde, lotg_vigente_hasta) VALUES
  (11, 1, ST_GeomFromText('MULTIPOLYGON(((-72.499 7.901, -72.495 7.901, -72.495 7.905, -72.499 7.905, -72.499 7.901)))', 4326), '2026-01-01 00:00+00', NULL),
  (12, 1, ST_GeomFromText('MULTIPOLYGON(((-72.494 7.901, -72.491 7.901, -72.491 7.904, -72.494 7.904, -72.494 7.901)))', 4326), '2026-01-01 00:00+00', '2026-03-01 00:00+00'),
  (12, 2, ST_GeomFromText('MULTIPOLYGON(((-72.494 7.901, -72.492 7.901, -72.492 7.903, -72.494 7.903, -72.494 7.901)))', 4326), '2026-03-01 00:00+00', NULL),
  (13, 1, ST_GeomFromText('MULTIPOLYGON(((-72.499 7.906, -72.497 7.906, -72.497 7.908, -72.499 7.908, -72.499 7.906)))', 4326), '2026-01-01 00:00+00', NULL);

INSERT INTO reticula (reti_id, pred_id, reti_resolucion_m) VALUES (1, 1, 100);
INSERT INTO reticula_celda (reti_id, retc_codigo, retc_geom) VALUES (1, 'A1', ST_GeomFromText('POLYGON((-72.50 7.90, -72.499 7.90, -72.499 7.901, -72.50 7.901, -72.50 7.90))', 4326));

INSERT INTO vigilancia (vigi_id, vigi_descripcion) VALUES (1, 'Vigilancia de prueba');
INSERT INTO trampa (tram_id, tram_codigo, tipt_id, atra_id, esta_id, tram_fecha_registro, tram_tecnico_registro_id)
SELECT v.id, v.cod, t.tipt_id, (SELECT min(atra_id) FROM atrayente), e.esta_id, DATE '2026-01-01', 1
  FROM (VALUES (1, '54125-R1-1'), (2, '54125-R1-3')) v(id, cod)
  JOIN tipo_trampa t ON t.tipt_descripcion = 'Jackson'
  JOIN estado_registro e ON e.esta_descripcion = 'activo';
INSERT INTO ubicacion_trampa (ubic_id, tram_id, pred_id, lote_id, ubic_fecha, ubic_fecha_fin, tecn_id, vigi_id, ubic_long, ubic_lat) VALUES
  (1, 1, 1, 11, DATE '2026-01-01', NULL,              1, 1, -72.497, 7.903),
  (2, 2, 1, 11, DATE '2026-01-01', DATE '2026-02-01', 1, 1, -72.496, 7.902);
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


def mapa(
    h: SimpleNamespace, bd: str, actor: Actor, pred_id: int, instante: datetime | None = None
) -> MapaPredio:
    async def _correr() -> MapaPredio:
        motor = create_async_engine(h.url(bd))
        try:
            async with motor.begin() as con:
                await con.execute(
                    text("SELECT set_config('sigat.usuario_actual', CAST(:u AS text), true)"),
                    {"u": str(actor.usua_id)},
                )
                return await ServicioPredios(RepositorioConfiguracion(con)).mapa(actor, pred_id, instante)
        finally:
            await motor.dispose()

    return asyncio.run(_correr())


# ------------------------------------------------------------------ validación GeoJSON (RFC 7946)
def _posicion_valida(p: Any) -> None:
    assert isinstance(p, list), p
    assert len(p) == 2, p
    lon, lat = p
    assert isinstance(lon, int | float)
    assert isinstance(lat, int | float)
    # EPSG:4326, orden lon, lat
    assert -180 <= lon <= 180, p
    assert -90 <= lat <= 90, p


def _anillo_valido(anillo: list[Any]) -> None:
    # Anillo cerrado y de al menos 4 posiciones.
    assert len(anillo) >= 4, anillo
    assert anillo[0] == anillo[-1], anillo
    for p in anillo:
        _posicion_valida(p)


def geometria_valida(g: dict[str, Any]) -> None:
    if g["type"] == "Point":
        _posicion_valida(g["coordinates"])
    elif g["type"] == "Polygon":
        for anillo in g["coordinates"]:
            _anillo_valido(anillo)
    elif g["type"] == "MultiPolygon":
        assert g["coordinates"]
        for poligono in g["coordinates"]:
            for anillo in poligono:
                _anillo_valido(anillo)
    else:  # pragma: no cover - la BD no guarda otros tipos en estas capas
        pytest.fail(f"tipo inesperado {g['type']}")


def _json(m: MapaPredio) -> dict[str, Any]:
    datos: dict[str, Any] = json.loads(m.model_dump_json())
    return datos


def _coleccion(c: dict[str, Any]) -> list[dict[str, Any]]:
    assert c["type"] == "FeatureCollection"
    features: list[dict[str, Any]] = c["features"]
    for f in features:
        assert f["type"] == "Feature"
        if f["geometry"] is not None:
            geometria_valida(f["geometry"])
    return features


# ------------------------------------------------------------------ predio autorizado con geometrías reales
def test_mapa_del_predio_de_ana_es_geojson_valido_con_sus_capas(h: SimpleNamespace, bd: str) -> None:
    datos = _json(mapa(h, bd, ANA, 1))

    predio = datos["predio"]
    assert predio["type"] == "Feature"
    assert predio["id"] == 1
    assert predio["properties"]["pred_nombre"] == "Predio Ana"
    assert predio["geometry"]["type"] == "MultiPolygon"
    geometria_valida(predio["geometry"])
    # Los vértices son los guardados en PostGIS (EPSG:4326, sin reproyección y en orden lon, lat).
    assert [-72.5, 7.9] in predio["geometry"]["coordinates"][0][0]
    assert [-72.49, 7.91] in predio["geometry"]["coordinates"][0][0]

    lotes = {f["id"]: f for f in _coleccion(datos["lotes"])}
    assert set(lotes) == {11, 12}  # el lote dado de baja no aparece
    assert lotes[11]["geometry"]["type"] == "MultiPolygon"
    assert [-72.499, 7.901] in lotes[11]["geometry"]["coordinates"][0][0]
    assert lotes[11]["properties"]["lote_codigo"] == "L11"

    celdas = _coleccion(datos["celdas"])
    assert [(c["properties"]["retc_codigo"], c["geometry"]["type"]) for c in celdas] == [("A1", "Polygon")]

    trampas = _coleccion(datos["trampas"])
    assert [t["properties"]["tram_codigo"] for t in trampas] == ["54125-R1-1"]  # la retirada no aparece
    assert trampas[0]["geometry"] == {"type": "Point", "coordinates": list(T1)}
    assert trampas[0]["properties"]["lote_id"] == 11


def test_el_mapa_usa_la_geometria_vigente_en_el_instante(h: SimpleNamespace, bd: str) -> None:
    def lote12(instante: datetime | None) -> list[Any]:
        lotes = {f["id"]: f for f in _json(mapa(h, bd, ANA, 1, instante))["lotes"]["features"]}
        coordenadas: list[Any] = lotes[12]["geometry"]["coordinates"][0][0]
        return coordenadas

    assert [-72.491, 7.904] in lote12(datetime(2026, 2, 15, tzinfo=UTC))  # v1
    assert [-72.492, 7.903] in lote12(None)  # hoy: v2
    # Antes de que existiera cualquier geometría del lote, el lote aparece sin geometría.
    previo = {
        f["id"]: f for f in _json(mapa(h, bd, ANA, 1, datetime(2025, 6, 1, tzinfo=UTC)))["lotes"]["features"]
    }
    assert previo[12]["geometry"] is None


# ------------------------------------------------------------------ sin geometrías
def test_predio_sin_geometrias_devuelve_colecciones_validas(h: SimpleNamespace, bd: str) -> None:
    datos = _json(mapa(h, bd, BRUNO, 2))
    assert datos["predio"]["geometry"] is None
    assert datos["predio"]["properties"]["pred_nombre"] == "Predio Bruno"
    lotes = _coleccion(datos["lotes"])
    assert [(f["id"], f["geometry"]) for f in lotes] == [(21, None)]
    assert _coleccion(datos["celdas"]) == []
    assert _coleccion(datos["trampas"]) == []


# ------------------------------------------------------------------ visibilidad y aislamiento
@pytest.mark.parametrize(("actor", "pred_id"), [(BRUNO, 1), (ANA, 2), (ANA, 999)])
def test_predio_ajeno_o_inexistente_da_404(h: SimpleNamespace, bd: str, actor: Actor, pred_id: int) -> None:
    with pytest.raises(NoEncontrado) as e:
        mapa(h, bd, actor, pred_id)
    assert e.value.codigo == "PREDIO_NO_ENCONTRADO"


def test_el_mapa_de_bruno_no_contiene_nada_de_ana(h: SimpleNamespace, bd: str) -> None:
    texto = mapa(h, bd, BRUNO, 2).model_dump_json()
    for ajeno in ("Predio Ana", "L11", "L12", "54125-R1-1", "-72.499"):
        assert ajeno not in texto


# ------------------------------------------------------------------ correspondencia con OpenAPI
def test_la_respuesta_corresponde_al_contrato(h: SimpleNamespace, bd: str) -> None:
    contrato = json.loads((RAIZ / "contracts" / "openapi.json").read_text(encoding="utf-8"))
    respuesta = contrato["paths"]["/api/v1/predios/{pred_id}/mapa"]["get"]["responses"]["200"]
    assert respuesta["content"]["application/json"]["schema"] == {"$ref": "#/components/schemas/MapaPredio"}
    esquema = contrato["components"]["schemas"]["MapaPredio"]
    datos = _json(mapa(h, bd, ANA, 1))
    assert set(esquema["required"]) <= set(datos)
    assert set(datos) <= set(esquema["properties"])
    assert MapaPredio.model_validate(datos) == mapa(h, bd, ANA, 1)  # ida y vuelta sin pérdida
