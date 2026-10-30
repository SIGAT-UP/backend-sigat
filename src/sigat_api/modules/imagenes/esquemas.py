"""Contrato HTTP de archivos y evidencia."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from sigat_api.compartido.esquemas import Esquema, GeometriaGeoJson
from sigat_api.compartido.tipos import ClaseArchivo, EstadoArchivo

MimePermitido = Literal[
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
]


class NuevoArchivo(Esquema):
    """Paso 1: el cliente declara el archivo. ``arch_id`` lo genera el cliente (idempotente)."""

    arch_id: UUID
    arch_clase: Literal["foto_evidencia", "foto_perfil", "documento_instruccion"]
    arch_nombre_original: str | None = Field(None, max_length=200)
    arch_mime: MimePermitido
    arch_tamano_bytes: int = Field(..., gt=0, description="Imágenes <= 8 MB, documentos <= 10 MB (config).")
    arch_hash_sha256: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    arch_paginas: int | None = Field(None, ge=1)
    arch_t_captura: datetime


class Archivo(Esquema):
    arch_id: UUID
    arch_clase: ClaseArchivo
    arch_nombre_original: str | None
    arch_mime: str
    arch_tamano_bytes: int
    arch_hash_sha256: str
    arch_paginas: int | None
    arch_estado: EstadoArchivo
    arch_motivo_rechazo: str | None
    arch_t_captura: datetime
    arch_t_sincronizacion: datetime
    arch_t_almacenado: datetime | None


class InstruccionSubida(Esquema):
    metodo: Literal["PUT"] = "PUT"
    url: str
    cabeceras: dict[str, str] = Field(..., description="Enviar tal cual (incluye Content-Type y checksum).")
    expira_en: int = Field(..., description="Segundos.")


class RespuestaNuevoArchivo(Esquema):
    archivo: Archivo
    subida: InstruccionSubida | None = Field(None, description="Nulo si el binario ya estaba almacenado.")


class VinculoEvidencia(Esquema):
    """Liga una foto a UNO de: lectura, hallazgo, visita o actividad planificada (plan_id + lote_id).

    Móvil: viaja como operación de sincronización ``entidad: "evidencia"``, ``registro_id = evid_id``.
    Web/en línea: ``POST /evidencias``; el backend crea esa misma operación con el dispositivo de la sesión.
    """

    evid_id: UUID = Field(..., description="Lo genera el cliente; idempotente.")
    arch_id: UUID
    lect_id: UUID | None = None
    hall_id: UUID | None = None
    visi_id: UUID | None = None
    plan_id: UUID | None = None
    lote_id: int | None = None
    evid_observacion: str = ""
    evid_geom: GeometriaGeoJson | None = None
    evid_precision_m: float | None = None


class Evidencia(VinculoEvidencia):
    usua_id: int
    evid_t_sincronizacion: datetime
    archivo: Archivo
