"""Contrato HTTP del catálogo."""

from typing import Any

from pydantic import Field

from sigat_api.compartido.esquemas import Esquema


class CatalogoInfo(Esquema):
    """Tarjeta del listado (web ``CatalogCard``)."""

    codigo: str
    titulo: str
    editable: bool
    total_items: int
    resumen: str = Field(..., description="Ej.: '4 valores: Normal, Dañada, …'")


class ItemCatalogo(Esquema):
    id: int
    descripcion: str
    codigo: int | str | None = None
    activo: bool = True
    atributos: dict[str, Any] = Field(
        default_factory=dict,
        description="Columnas propias del catálogo (p. ej. vida útil del atrayente, paridad del tipo de trampa).",
    )


class ItemCatalogoEntrada(Esquema):
    id: int | None = Field(None, description="Nulo = valor nuevo.")
    descripcion: str = Field(..., min_length=1, max_length=200)
    codigo: int | str | None = None
    activo: bool = True
    atributos: dict[str, Any] = Field(default_factory=dict)


class ReemplazoCatalogo(Esquema):
    """Semántica de conjunto (web ``saveCatalogItems``): los ausentes se RETIRAN, no se borran."""

    items: list[ItemCatalogoEntrada] = Field(..., min_length=1)


class Departamento(Esquema):
    depa_id: int
    depa_codigo: str | None
    depa_descripcion: str


class Municipio(Esquema):
    muni_id: int
    muni_codigo: str | None
    muni_descripcion: str
    depa_id: int
    divipola: str | None = Field(None, description="v_municipio_divipola (5 dígitos).")
