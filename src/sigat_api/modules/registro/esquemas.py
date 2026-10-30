"""Contrato HTTP del núcleo de registro e historial."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import Field

from sigat_api.compartido.esquemas import Esquema
from sigat_api.compartido.tipos import AccionSync, EstadoRevision, EstadoRevisionLectura, Linaje


# ------------------------------------------------------------------ visitas
class Visita(Esquema):
    visi_id: UUID
    usua_id: int
    tecnico: str
    pred_id: int
    pred_nombre: str
    ruta_id: int | None
    t_inicio_obs: datetime
    t_fin_obs: datetime
    t_captura: datetime
    t_sincronizacion: datetime
    deriva_reloj_seg: int | None
    estado_revision: EstadoRevision
    motivo_revision: str | None
    revisada_por: int | None
    revisada_en: datetime | None
    lote_ids: list[int]
    lotes: list[str] = Field(..., description="Códigos de lote (v_registro_campo.lotes).")
    trampas_leidas: int


# ------------------------------------------------------------------ lecturas
class Lectura(Esquema):
    """Versión de ``lectura_trampa`` (por defecto la vigente: v_lectura_vigente)."""

    lect_id: UUID
    lect_registro_id: UUID
    lect_version: int
    visi_id: UUID
    tram_id: int
    tram_codigo: str
    lote_id: int | None
    ubic_id: int | None
    lect_leida: bool
    lect_especimenes: int | None
    lect_justificacion: str | None
    cond_id: int
    condicion: str
    lect_fecha_cambio_cuerpo: date | None
    lect_fecha_cambio_atrayente: date | None
    atra_id: int | None
    lect_observaciones: str | None
    latitud: Decimal | None
    longitud: Decimal | None
    lect_precision_m: float | None
    lect_coincide_lote: bool | None
    linaje: Linaje
    usua_id: int
    autor: str
    t_observacion: datetime
    t_captura: datetime
    t_sincronizacion: datetime
    deriva_reloj_seg: int | None
    anulada: bool
    motivo_anulacion: str | None
    motivo_correccion: str | None = Field(None, description="lect_motivo_correccion (BD v9), versión >= 2.")
    especimenes_originales: int | None = Field(
        None, description="Valor de la versión 1 (v_lectura_revision)."
    )
    estado_revision: EstadoRevisionLectura = Field(
        EstadoRevisionLectura.SIN_VERIFICAR,
        description="Derivado en v_lectura_revision: sin_verificar, confirmado, corregido, rechazado, autorreporte.",
    )
    evidencias: int = 0


class VisitaDetalle(Visita):
    lecturas: list[Lectura]


class VersionRegistro(Esquema):
    version: int
    accion: AccionSync
    anulada: bool
    motivo: str | None
    autor: str
    usua_id: int
    t_sincronizacion: datetime
    valores: dict[str, Any] = Field(..., description="Columnas de dominio de esa versión.")


class HistorialVersiones(Esquema):
    """RF-052: 'qué se registró originalmente el lunes' siempre tiene respuesta."""

    entidad: str
    registro_id: UUID
    t_observacion: datetime
    versiones: list[VersionRegistro]


class CorreccionLectura(Esquema):
    """Agrónomo corrige el número de especímenes -> versión n+1 (ADR-03) con
    ``lect_motivo_correccion`` = motivo (BD v9). t_observacion NO cambia."""

    lect_especimenes: int = Field(..., ge=0)
    motivo: str = Field(..., min_length=10, max_length=500)
    cond_id: int | None = None
    lect_observaciones: str | None = Field(None, max_length=1000)


class AnulacionRegistro(Esquema):
    """Rechazo = versión n+1 con ``*_anulada = true`` y su motivo. Nada se borra (RN-009)."""

    motivo: str = Field(..., min_length=10, max_length=500)


# ------------------------------------------------------------------ revisión del agrónomo
class RegistroRevision(Esquema):
    """Fila de ``v_registro_campo`` (+ advertencias calculadas)."""

    visi_id: UUID
    usua_id: int
    tecnico: str
    pred_id: int
    pred_nombre: str
    observada_el: datetime
    recibida_el: datetime
    lotes: list[str]
    trampas_leidas: int
    estado_revision: EstadoRevision
    motivo_revision: str | None
    advertencias: list[str] = Field(
        default_factory=list,
        description="Trampa fuera del lote, lote no asignado ese día (v_visita_lote_sin_asignacion), deriva de reloj…",
    )


class RevisionDetalle(RegistroRevision):
    lecturas: list[Lectura]
    versiones: list[HistorialVersiones] = Field(default_factory=list)


class ObservacionRevision(Esquema):
    motivo: str = Field(..., min_length=10, max_length=500)


# ------------------------------------------------------------------ autorreporte del productor
class Aplicacion(Esquema):
    apli_id: UUID
    apli_registro_id: UUID
    apli_version: int
    lote_id: int
    lote_descripcion: str
    prof_id: int | None
    producto: str = Field(..., description="Nombre del catálogo o apli_producto_texto.")
    apli_dosis: Decimal
    dosis_unidad: str
    apli_area_tratada: Decimal
    area_unidad: str
    responsable: str | None
    apli_observaciones: str | None
    linaje: Linaje
    t_observacion: datetime
    t_captura: datetime
    t_sincronizacion: datetime
    anulada: bool


class NuevaAplicacion(Esquema):
    """Alta en línea (web). ``apli_registro_id`` lo genera el cliente (UUID v7) para que
    reintentar no duplique (misma idempotencia que el sync)."""

    apli_registro_id: UUID
    lote_id: int
    prof_id: int | None = None
    apli_producto_texto: str | None = Field(
        None, max_length=150, description="Obligatorio si prof_id es nulo."
    )
    apli_dosis: Decimal = Field(..., gt=0)
    apli_dosis_uni_id: int
    apli_area_tratada: Decimal = Field(..., gt=0)
    apli_area_uni_id: int
    pers_cc_responsable: int | None = None
    apli_responsable_nombre: str | None = Field(None, max_length=150)
    apli_observaciones: str | None = Field(None, max_length=1000)
    t_observacion: datetime


class Cosecha(Esquema):
    cose_id: UUID
    cose_registro_id: UUID
    cose_version: int
    lote_id: int
    lote_descripcion: str
    cose_fecha_esperada: date
    cose_volumen_esperado: Decimal
    cose_fecha_real: date | None
    cose_volumen_real: Decimal | None
    unidad: str
    cose_metodo_registro: str | None
    cose_observaciones: str | None
    linaje: Linaje
    t_observacion: datetime
    anulada: bool


class NuevaCosecha(Esquema):
    cose_registro_id: UUID
    lote_id: int
    cose_fecha_esperada: date
    cose_volumen_esperado: Decimal = Field(..., ge=0)
    cose_fecha_real: date | None = None
    cose_volumen_real: Decimal | None = Field(None, ge=0)
    cose_volumen_uni_id: int
    cose_metodo_registro: str | None = Field(None, max_length=100)
    cose_observaciones: str | None = Field(None, max_length=1000)
    t_observacion: datetime


class NuevaVersionAutorreporte(Esquema):
    """Corrección (``corregir``) o anulación (``anular``) de una aplicación o cosecha.
    ``cambios`` usa los nombres de columna de la tabla (sin *_registro_id ni *_version)."""

    accion: Literal["corregir", "anular"]
    version_esperada: int = Field(..., ge=1, description="Versión vigente que se corrige (concurrencia).")
    cambios: dict[str, Any] = Field(default_factory=dict)
    motivo: str = Field(..., min_length=5, max_length=500)


# ------------------------------------------------------------------ historial / actividad
class EntradaActividad(Esquema):
    """``v_actividad_lote`` ampliada. Alimenta: web historial del lote y del productor,
    línea de tiempo, móvil ``ActivityRecord``."""

    lote_id: int
    lote_descripcion: str
    tipo: Literal["vigilancia", "aplicacion", "cosecha", "correccion", "hallazgo", "etapa"]
    registro_id: UUID
    t_observacion: datetime
    usua_id: int
    autor: str
    rol_autor: str
    linaje: Linaje
    titulo: str
    detalle: str | None


class ActividadReciente(Esquema):
    tipo: Literal["sincronizacion", "visita", "lectura", "aplicacion"]
    texto: str
    t: datetime
