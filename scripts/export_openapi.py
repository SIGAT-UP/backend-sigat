"""Publica el contrato OpenAPI como artefacto versionado.

Uso:
    uv run python -m scripts.export_openapi
"""

import json
from pathlib import Path

from ica_api.main import app


def main() -> None:
    destino = Path("contracts/openapi.json")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"contrato escrito en {destino}")


if __name__ == "__main__":
    main()
