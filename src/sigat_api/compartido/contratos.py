"""Contratos EN PROCESO entre módulos (ADR-14: comunicación por contrato, no por tablas).

Aquí solo viven los tipos que cruzan una frontera de módulo. Un módulo que
ofrece una capacidad la implementa; el que la consume declara un ``Protocol``
en su ``puertos.py`` con estos tipos. ``api/fabricas.py`` los conecta.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sigat_api.compartido.tipos import AccionSync, Actor, ClasificacionOperacion, EntidadSync, Linaje


@dataclass(frozen=True, slots=True)
class OperacionCampo:
    """Operación de campo ya autenticada, con forma válida y no repetida (la entrega Sincronización)."""

    oper_id: int  # fila de operacion_sync ya insertada en esta transacción
    cliente_id: UUID
    disp_id: UUID
    entidad: EntidadSync
    accion: AccionSync
    registro_id: UUID
    version: int
    linaje: Linaje | None
    t_observacion: datetime
    t_captura: datetime
    deriva_reloj_seg: int | None
    datos: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ResultadoAplicacion:
    """Lo que devuelve el núcleo de Registro al aplicar una operación."""

    clasificacion: ClasificacionOperacion
    motivo: str | None = None
    codigo: str | None = None
    periodos_afectados: list[int] = field(default_factory=list)  # peri_id a reprocesar (RF-054)
    fecha_efecto: datetime | None = None


@dataclass(frozen=True, slots=True)
class PeriodoRef:
    peri_id: int
    lote_id: int
    inicio: date
    fin: date
    abierto: bool


@dataclass(frozen=True, slots=True)
class PertenenciaTrampa:
    tram_id: int
    ubic_id: int | None
    lote_id: int | None
    pred_id: int
    lote_activo: bool


__all__ = [
    "Actor",
    "OperacionCampo",
    "PeriodoRef",
    "PertenenciaTrampa",
    "ResultadoAplicacion",
]
