"""Migración 0010 (ampliación de ``v_planificacion``): coherencia sin base de datos."""

import importlib.util
import re
from pathlib import Path
from types import ModuleType

RAIZ = Path(__file__).resolve().parents[2]
SQL = RAIZ / "bd" / "sql"
ARCHIVO_SQL = SQL / "19_ampliacion_v_planificacion.sql"
MIGRACION = RAIZ / "migrations" / "versions" / "0010_ampliacion_v_planificacion.py"


def _cargar(ruta: Path, nombre: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    assert spec is not None
    assert spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _normalizado(sql: str) -> str:
    return re.sub(r"\s+", " ", sql).strip()


def test_cadena_de_revisiones() -> None:
    m = _cargar(MIGRACION, "migracion_0010")
    assert (m.revision, m.down_revision) == ("0010", "0009")
    assert m.ARCHIVO == ARCHIVO_SQL


def test_no_es_destructiva_y_esta_registrada() -> None:
    revisor = _cargar(RAIZ / "scripts" / "revisar_migraciones.py", "revisar_migraciones")
    destructivas, problemas = revisor.revisar(
        ["migrations/versions/0010_ampliacion_v_planificacion.py", "bd/sql/19_ampliacion_v_planificacion.sql"]
    )
    assert destructivas == []
    assert problemas == []


def test_instalacion_por_psql_incluye_el_archivo_al_final() -> None:
    lineas = [x.strip() for x in (SQL / "00_instalar_todo.sql").read_text(encoding="utf-8").splitlines()]
    assert (
        lineas.index(r"\ir 19_ampliacion_v_planificacion.sql")
        == lineas.index(r"\ir 18_vista_notificacion_app.sql") + 1
    )


def test_el_sql_solo_reemplaza_la_vista() -> None:
    texto = re.sub(r"--.*", "", ARCHIVO_SQL.read_text(encoding="utf-8"))
    sin_literales = re.sub(r"'([^']|'')*'", "''", texto)
    assert re.findall(r"CREATE OR REPLACE VIEW (\S+)", sin_literales) == ["sigat.v_planificacion"]
    assert not re.search(r"\b(DROP|ALTER|INSERT|UPDATE|DELETE|TRUNCATE|CREATE TABLE)\b", sin_literales)


def test_el_downgrade_restaura_exactamente_la_vista_de_03() -> None:
    original = (SQL / "03_vistas.sql").read_text(encoding="utf-8")
    inicio = original.index("CREATE OR REPLACE VIEW v_planificacion AS")
    fin = original.index("\n", original.index("COMMENT ON VIEW v_planificacion", inicio))
    m = _cargar(MIGRACION, "migracion_0010_downgrade")
    restaurada = m.VISTA_ANTERIOR.split("\n", 2)[2]
    assert _normalizado(restaurada) == _normalizado(
        original[inicio:fin].replace("CREATE OR REPLACE VIEW", "CREATE VIEW", 1)
    )
