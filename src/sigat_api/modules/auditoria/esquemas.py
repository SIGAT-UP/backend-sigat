"""Contrato HTTP de auditoría (web ``AuditEntry``)."""

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from sigat_api.compartido.esquemas import Esquema

CategoriaAuditoria = Literal["Usuarios", "Predio", "Sistema", "Registros", "Trampas", "Configuración"]


class EntradaAuditoria(Esquema):
    bita_id: int
    bita_t_registro: datetime
    usua_id: int | None
    usuario: str | None
    bita_tabla: str
    bita_registro: str
    bita_accion: Literal["INSERT", "UPDATE", "DELETE", "ACCESO", "SYNC"]
    categoria: CategoriaAuditoria = Field(..., description="Derivada de bita_tabla.")
    resumen: str = Field(..., description="Texto legible: 'Trampa creada · 54518-602-001'.")
    detalle: dict[str, Any] | None = Field(None, description="Solo con ?con_detalle=true.")
