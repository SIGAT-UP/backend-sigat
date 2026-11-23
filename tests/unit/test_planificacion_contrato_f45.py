"""F4/F5: el esquema ``Planificacion`` (y por tanto el contrato OpenAPI) expone las columnas que la
migración 0010 agregó a ``v_planificacion``. Sin base de datos."""

import json
from pathlib import Path

from sigat_api.modules.planificacion.esquemas import Planificacion

RAIZ = Path(__file__).resolve().parents[2]

# Campo -> tipo no nulo esperado en el contrato (todos admiten null salvo lotes_descripcion).
CAMPOS_F45 = {
    "arch_id_documento": "string",
    "plan_documento_clase": "string",
    "documento_mime": "string",
    "documento_bytes": "integer",
    "documento_paginas": "integer",
    "plan_motivo_rechazo": "string",
}


def _esquema_contrato() -> dict[str, object]:
    contrato = json.loads((RAIZ / "contracts" / "openapi.json").read_text(encoding="utf-8"))
    esquemas = contrato["components"]["schemas"]
    # FastAPI separa el modelo de respuesta en "-Output" cuando el de entrada difiere.
    nombre = "Planificacion" if "Planificacion" in esquemas else "Planificacion-Output"
    esquema: dict[str, object] = esquemas[nombre]
    return esquema


def test_el_esquema_tiene_los_campos_de_f45() -> None:
    campos = Planificacion.model_fields
    for campo in (*CAMPOS_F45, "lotes_descripcion"):
        assert campo in campos, campo
    # Los nuevos son opcionales: una planificación sin documento ni rechazo sigue siendo válida.
    for campo in ("plan_documento_clase", "documento_mime", "documento_bytes", "documento_paginas"):
        assert campos[campo].default is None, campo
    assert campos["plan_motivo_rechazo"].default is None


def test_el_contrato_expone_los_campos_con_su_tipo_y_nulabilidad() -> None:
    propiedades = _esquema_contrato()["properties"]
    assert isinstance(propiedades, dict)
    for campo, tipo in CAMPOS_F45.items():
        variantes = propiedades[campo]["anyOf"]
        assert {"type": "null"} in variantes, campo
        assert any(v.get("type") == tipo for v in variantes), campo
    assert propiedades["lotes_descripcion"]["type"] == "array"
    assert propiedades["lotes_descripcion"]["items"] == {"type": "string"}
