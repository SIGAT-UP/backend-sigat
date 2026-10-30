"""Revisión de los cambios de base de datos de una rama (lo corre la CI en cada pull request).

Qué revisa en los archivos de ``migrations/versions/`` y ``bd/`` que cambian respecto a la rama base:

1. **Operaciones destructivas**: eliminan tablas, columnas, relaciones (restricciones) o datos
   (``DROP TABLE``, ``DROP COLUMN``, ``DROP CONSTRAINT``, ``DROP SCHEMA``, ``TRUNCATE``, ``DELETE FROM``,
   ``UPDATE … SET``, ``op.drop_*``). Si aparece alguna, el chequeo FALLA hasta que un revisor ponga la
   etiqueta ``bd-destructivo-aprobado`` al pull request (la CI la convierte en
   ``SIGAT_BD_DESTRUCTIVO_APROBADO=1``). En las migraciones de Alembic solo se mira ``upgrade()``.
2. **Registro**: cada migración nueva debe estar descrita en ``bd/CAMBIOS.md`` (por su revisión).
3. **Volcados y secretos**: no se aceptan volcados de bases (``pg_dump``, ``COPY … FROM stdin``,
   ``.dump``/``.backup``) ni hashes de contraseña (``$argon2id$``, ``$2b$``) en archivos SQL.

Uso::

    python scripts/revisar_migraciones.py                 # contra origin/main
    python scripts/revisar_migraciones.py --base main
    python scripts/revisar_migraciones.py --todo          # todo el repositorio (informativo)
"""

import argparse
import ast
import os
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CARPETAS = ("migrations/versions/", "bd/")
CAMBIOS = RAIZ / "bd" / "CAMBIOS.md"

DESTRUCTIVAS = [
    (re.compile(r"\bDROP\s+TABLE\b", re.I), "elimina una tabla"),
    (re.compile(r"\bDROP\s+SCHEMA\b", re.I), "elimina un esquema"),
    (re.compile(r"\bDROP\s+COLUMN\b", re.I), "elimina una columna"),
    (re.compile(r"\bDROP\s+CONSTRAINT\b", re.I), "elimina una restricción o relación"),
    (re.compile(r"^\s*TRUNCATE\b", re.I), "vacía una tabla"),
    (re.compile(r"\bDELETE\s+FROM\b", re.I), "borra filas"),
    (re.compile(r"\bUPDATE\s+[\w.\"]+\s+SET\b", re.I), "modifica filas existentes"),
    (re.compile(r"\bop\.drop_\w+\("), "operación drop de Alembic"),
]
VOLCADOS = [
    (re.compile(r"PostgreSQL database dump"), "parece un volcado de pg_dump"),
    (re.compile(r"\bCOPY\s+[\w.\"]+\s*(\([^)]*\))?\s+FROM\s+stdin\b", re.I), "datos copiados de una base"),
    (re.compile(r"\$(argon2id|2[aby])\$"), "contiene un hash de contraseña"),
]
EXTENSIONES_VOLCADO = {".dump", ".backup", ".bak", ".tar.gz", ".gz"}


def _git(*args: str) -> str:
    return subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def archivos_cambiados(base: str) -> list[str]:
    salida = _git("diff", "--name-only", "--diff-filter=AMR", f"{base}...HEAD")
    return [a for a in salida.splitlines() if a.startswith(CARPETAS)]


def archivos_todos() -> list[str]:
    return [a for a in _git("ls-files").splitlines() if a.startswith(CARPETAS)]


def _sin_comentarios_sql(texto: str) -> str:
    """Quita comentarios y los cuerpos de funciones (``$$ … $$``): lo que va dentro de una función se
    ejecuta cuando alguien la llama, no al aplicar la migración. Conserva los saltos de línea para
    que los números de línea del informe coincidan con el archivo."""
    texto = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), texto, flags=re.S)
    texto = re.sub(
        r"\$(\w*)\$.*?\$\1\$", lambda m: "$$" + "\n" * m.group(0).count("\n") + "$$", texto, flags=re.S
    )
    return "\n".join(linea.split("--", 1)[0] for linea in texto.splitlines())


def _texto_upgrade(fuente: str) -> str:
    """Solo el cuerpo de ``upgrade()`` (``downgrade()`` puede, y suele, deshacer con DROP)."""
    arbol = ast.parse(fuente)
    for nodo in arbol.body:
        if isinstance(nodo, ast.FunctionDef) and nodo.name == "upgrade":
            return ast.get_source_segment(fuente, nodo) or ""
    return ""


def revisar(rutas: list[str]) -> tuple[list[str], list[str]]:
    destructivas: list[str] = []
    problemas: list[str] = []
    registro = CAMBIOS.read_text(encoding="utf-8") if CAMBIOS.exists() else ""
    for ruta in rutas:
        archivo = RAIZ / ruta
        if not archivo.exists():
            continue
        if any(ruta.endswith(ext) for ext in EXTENSIONES_VOLCADO):
            problemas.append(f"{ruta}: no se suben volcados ni respaldos de bases de datos.")
            continue
        texto = archivo.read_text(encoding="utf-8", errors="replace")
        if ruta.endswith(".sql"):
            for patron, motivo in VOLCADOS:
                if patron.search(texto):
                    problemas.append(f"{ruta}: {motivo}.")
            revisado = _sin_comentarios_sql(texto)
        elif ruta.startswith("migrations/versions/") and ruta.endswith(".py"):
            revision = re.search(r"^revision\s*=\s*[\"'](\w+)[\"']", texto, re.M)
            if revision and f"`{revision.group(1)}`" not in registro:
                problemas.append(f"{ruta}: describa la revisión {revision.group(1)} en bd/CAMBIOS.md.")
            revisado = _texto_upgrade(texto)
        else:
            continue
        for numero, linea in enumerate(revisado.splitlines(), 1):
            for patron, motivo in DESTRUCTIVAS:
                if patron.search(linea):
                    destructivas.append(f"{ruta}:{numero}: {motivo}: {linea.strip()[:100]}")
    return destructivas, problemas


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--base", default=os.environ.get("SIGAT_RAMA_BASE", "origin/main"))
    p.add_argument("--todo", action="store_true", help="Revisa todo el repositorio y solo informa")
    a = p.parse_args()
    rutas = archivos_todos() if a.todo else archivos_cambiados(a.base)
    destructivas, problemas = revisar(rutas)
    aprobado = os.environ.get("SIGAT_BD_DESTRUCTIVO_APROBADO") == "1"

    print(f"Archivos de base de datos revisados: {len(rutas)}")
    for p_ in problemas:
        print(f"  ERROR  {p_}")
    for d in destructivas:
        print(f"  {'APROBADO' if aprobado else 'DESTRUCTIVO'}  {d}")
    if a.todo:
        return
    if problemas:
        sys.exit(1)
    if destructivas and not aprobado:
        print(
            "\nEste cambio elimina o modifica estructura o datos. Necesita una justificación técnica en el "
            "pull request y la revisión del responsable de la base de datos, que pone la etiqueta "
            "'bd-destructivo-aprobado'. Mientras tanto no se fusiona."
        )
        sys.exit(1)
    print("Sin cambios destructivos pendientes de aprobación.")


if __name__ == "__main__":
    main()
