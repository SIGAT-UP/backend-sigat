"""Migración 0009 (``v_notificacion_app``): coherencia sin base de datos."""

import importlib.util
import re
from pathlib import Path
from types import ModuleType

RAIZ = Path(__file__).resolve().parents[2]
SQL = RAIZ / "bd" / "sql"
ARCHIVO_SQL = SQL / "18_vista_notificacion_app.sql"
MIGRACION = RAIZ / "migrations" / "versions" / "0009_vista_notificacion_app.py"
REPOSITORIO = RAIZ / "src" / "sigat_api" / "modules" / "notificaciones" / "repositorio.py"


def _cargar(ruta: Path, nombre: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    assert spec is not None
    assert spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_cadena_de_revisiones() -> None:
    m = _cargar(MIGRACION, "migracion_0009")
    assert (m.revision, m.down_revision) == ("0009", "0008")
    assert m.ARCHIVO == ARCHIVO_SQL
    assert m.VISTA == "sigat.v_notificacion_app"


def test_no_es_destructiva_y_esta_registrada() -> None:
    revisor = _cargar(RAIZ / "scripts" / "revisar_migraciones.py", "revisar_migraciones")
    destructivas, problemas = revisor.revisar(
        ["migrations/versions/0009_vista_notificacion_app.py", "bd/sql/18_vista_notificacion_app.sql"]
    )
    assert destructivas == []
    assert problemas == []


def test_instalacion_por_psql_incluye_el_archivo_al_final() -> None:
    lineas = [x.strip() for x in (SQL / "00_instalar_todo.sql").read_text(encoding="utf-8").splitlines()]
    assert (
        lineas.index(r"\ir 18_vista_notificacion_app.sql")
        == lineas.index(r"\ir 17_vistas_informe_local.sql") + 1
    )


def test_el_sql_solo_crea_la_vista() -> None:
    texto = re.sub(r"--.*", "", ARCHIVO_SQL.read_text(encoding="utf-8"))
    sin_literales = re.sub(r"'([^']|'')*'", "''", texto)
    assert re.findall(r"CREATE OR REPLACE VIEW (\S+)", sin_literales) == ["sigat.v_notificacion_app"]
    assert not re.search(r"\b(DROP|ALTER|INSERT|UPDATE|DELETE|TRUNCATE|CREATE TABLE)\b", sin_literales)


def test_solo_el_repositorio_de_notificaciones_lee_la_vista() -> None:
    usos = {
        archivo.relative_to(RAIZ).as_posix()
        for archivo in (RAIZ / "src").rglob("*.py")
        if "v_notificacion_app" in archivo.read_text(encoding="utf-8")
    }
    assert usos == {"src/sigat_api/modules/notificaciones/repositorio.py"}


def test_toda_lectura_de_la_vista_filtra_por_el_usuario() -> None:
    """La vista devuelve los avisos de todos: cada consulta debe limitarse al usua_id del token."""
    fuente = REPOSITORIO.read_text(encoding="utf-8")
    consultas = re.findall(r'_COLUMNAS\s*\+\s*"""(.*?)"""', fuente, re.S)
    assert consultas
    assert all(c.strip().startswith("WHERE n.usua_id = :u") for c in consultas)
    assert fuente.count("_COLUMNAS") == len(consultas) + 1
