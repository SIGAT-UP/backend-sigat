"""Genera ``contracts/openapi.json`` desde el código (Arquitectura §9.1: el contrato lo publica el servidor).

python scripts/exportar_openapi.py              # escribe el archivo
python scripts/exportar_openapi.py --verificar  # falla si el archivo versionado no coincide (CI)
"""

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from sigat_api.main import crear_app  # noqa: E402

DESTINO = RAIZ / "contracts" / "openapi.json"


def generar() -> str:
    return json.dumps(crear_app().openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    contenido = generar()
    if "--verificar" in sys.argv:
        actual = DESTINO.read_text(encoding="utf-8") if DESTINO.exists() else ""
        if actual != contenido:
            print("contracts/openapi.json no coincide con el código. Ejecute: make contrato", file=sys.stderr)
            return 1
        print("Contrato sincronizado.")
        return 0
    DESTINO.write_text(contenido, encoding="utf-8")
    print(f"Escrito {DESTINO.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
