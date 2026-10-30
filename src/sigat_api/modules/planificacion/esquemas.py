"""Contrato HTTP de planificación. Campos = ``v_planificacion`` (móvil ``Planning.fromApi``)."""

from datetime import date, datetime, time
from typing import Literal
from uuid import UUID

from pydantic import Field

from sigat_api.compartido.esquemas import Esquema
from sigat_api.compartido.tipos import EstadoPlanificacion, EstadoPlanLote


class Planificacion(Esquema):
    plan_id: UUID
    tipo: Literal["productor", "tecnico"] = Field(
        ..., description="Derivado de rol_destinatario / plan_id_origen."
    )
    plan_actividad: str
    plan_fecha_inicio: date
    plan_fecha_fin: date | None
    plan_hora_desde: time | None
    plan_hora_hasta: time | None
    plan_estado: EstadoPlanificacion
    plan_observaciones: str | None
    plan_observacion_respuesta: str | None = Field(
        None, description="Motivo de rechazo u observación de aceptación."
    )
    plan_creada_en: datetime
    plan_respondida_en: datetime | None
    usua_id_destinatario: int
    destinatario: str
    rol_destinatario: str
    usua_id_creador: int
    creador: str
    arch_id_documento: UUID | None
    documento: str | None = Field(None, description="Nombre original del documento adjunto.")
    lotes: list[str] = Field(..., description="Códigos de lote.")
    lote_ids: list[int]
    plan_id_origen: UUID | None
    usua_id_respuesta: int | None
    respondio: str | None
    lotes_pendientes: int
    lotes_ejecutados: int
    lotes_no_ejecutados: int


class ResultadoLote(Esquema):
    lote_id: int
    lote_codigo: str | None
    plal_sync_id: UUID = Field(
        ..., description="Registro lógico para el sync offline (entidad planificacion_lote)."
    )
    plal_estado: EstadoPlanLote
    plal_observacion: str | None
    plal_resuelta_en: datetime | None
    visi_id: UUID | None
    evidencias: int


class PlanificacionDetalle(Planificacion):
    resultados_lote: list[ResultadoLote]


class NuevaPlanificacion(Esquema):
    usua_id_destinatario: int
    plan_actividad: str = Field(..., min_length=3, max_length=200)
    plan_fecha_inicio: date
    plan_fecha_fin: date | None = None
    plan_hora_desde: time | None = None
    plan_hora_hasta: time | None = None
    plan_observaciones: str | None = Field(None, max_length=2000)
    arch_id_documento: UUID | None = Field(None, description="documento_instruccion ya subido por /archivos.")
    lote_ids: list[int] = Field(default_factory=list)
    plan_id_origen: UUID | None = Field(None, description="Obligatorio si el destinatario es TÉCNICO.")


class Aceptacion(Esquema):
    observacion: str | None = Field(None, max_length=500)


class Rechazo(Esquema):
    motivo: str = Field(..., min_length=10, max_length=500)


class EntradaResultadoLote(Esquema):
    plal_estado: Literal["ejecutada", "no_ejecutada"]
    plal_observacion: str | None = Field(None, max_length=1000, description="Obligatoria si no_ejecutada.")
    visi_id: UUID | None = Field(None, description="Visita que respalda la ejecución (opcional).")


class Destinatario(Esquema):
    usua_id: int
    nombre: str
    subtitulo: str = Field(..., description="Ej.: 'Productor · Finca El Mirador'.")
    tipo: Literal["productor", "tecnico"]


class LoteAsignable(Esquema):
    lote_id: int
    lote_codigo: str | None
    lote_descripcion: str
    pred_id: int
    pred_nombre: str


class ActividadTecnico(Esquema):
    """Fila de ``v_actividad_tecnico`` (informe de actividades realizadas y no realizadas)."""

    plan_id: UUID
    plan_id_origen: UUID | None
    planificacion_aprobada: str | None
    aprobada_el: datetime | None
    plan_actividad: str
    plan_fecha_inicio: date
    plan_fecha_fin: date | None
    actividad_estado: EstadoPlanificacion
    usua_id: int
    tecnico: str
    lote_id: int
    lote_codigo: str | None
    pred_id: int
    resultado: EstadoPlanLote
    justificacion: str | None
    resuelta_en: datetime | None
    visi_id: UUID | None
    evidencias: int
