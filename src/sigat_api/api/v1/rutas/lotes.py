"""Lotes: datos, geometría versionada, programa, resumen fitosanitario, MTD, concepto e historial."""

from datetime import date, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status

from sigat_api.api.dependencias import ActorDep, requiere
from sigat_api.api.fabricas import (
    servicio_concepto,
    servicio_consulta_registro,
    servicio_lotes,
    servicio_programa,
)
from sigat_api.api.v1.comunes import ERRORES, Cursor
from sigat_api.compartido.esquemas import Pagina
from sigat_api.compartido.tipos import Actor
from sigat_api.modules.concepto import esquemas as ec
from sigat_api.modules.concepto.servicio import ServicioConcepto
from sigat_api.modules.configuracion import esquemas as e
from sigat_api.modules.configuracion.servicio import ServicioLotes, ServicioPrograma
from sigat_api.modules.registro import esquemas as er
from sigat_api.modules.registro.servicio import ServicioConsultaRegistro

router = APIRouter(prefix="/lotes", tags=["Lotes"], responses=ERRORES)
Lotes = Annotated[ServicioLotes, Depends(servicio_lotes)]
Concepto = Annotated[ServicioConcepto, Depends(servicio_concepto)]
Consulta = Annotated[ServicioConsultaRegistro, Depends(servicio_consulta_registro)]


@router.get("", response_model=list[e.Lote], summary="Lotes visibles para mí (técnico: asignados)")
async def listar(
    actor: ActorDep,
    svc: Lotes,
    pred_id: int | None = None,
    incluir: Annotated[list[Literal["indicadores"]] | None, Query()] = None,
) -> list[e.Lote]:
    return await svc.listar(actor, pred_id, "indicadores" in (incluir or []))


@router.get("/{lote_id}", response_model=e.LoteDetalle, summary="Detalle del lote")
async def obtener(lote_id: int, actor: ActorDep, svc: Lotes) -> e.LoteDetalle:
    return await svc.obtener(actor, lote_id)


@router.patch("/{lote_id}", response_model=e.LoteDetalle, summary="Actualizar lote")
async def actualizar(
    lote_id: int,
    s: e.ActualizacionLote,
    actor: Annotated[Actor, Depends(requiere("lotes.editar"))],
    svc: Lotes,
) -> e.LoteDetalle:
    return await svc.actualizar(actor, lote_id, s)


@router.get(
    "/{lote_id}/geometrias",
    response_model=list[e.VersionGeometriaLote],
    summary="Versiones de la geometría (ADR-06)",
)
async def geometrias(lote_id: int, actor: ActorDep, svc: Lotes) -> list[e.VersionGeometriaLote]:
    return await svc.geometrias(actor, lote_id)


@router.post(
    "/{lote_id}/geometrias",
    response_model=e.VersionGeometriaLote,
    status_code=status.HTTP_201_CREATED,
    summary="Nueva versión de la geometría del lote",
)
async def nueva_geometria(
    lote_id: int,
    s: e.EntradaGeometria,
    actor: Annotated[Actor, Depends(requiere("lotes.editar"))],
    svc: Lotes,
) -> e.VersionGeometriaLote:
    return await svc.nueva_geometria(actor, lote_id, s)


@router.get(
    "/{lote_id}/programa", response_model=e.ProgramaInspeccion, summary="Programa vigente del lote (móvil)"
)
async def programa(
    lote_id: int, actor: ActorDep, svc: Annotated[ServicioPrograma, Depends(servicio_programa)]
) -> e.ProgramaInspeccion:
    return await svc.de_lote(actor, lote_id)


@router.get(
    "/{lote_id}/resumen",
    response_model=ec.ResumenLote,
    summary="Resumen fitosanitario (MTD, umbral, concepto)",
)
async def resumen(lote_id: int, actor: ActorDep, svc: Concepto) -> ec.ResumenLote:
    return await svc.resumen_lote(actor, lote_id)


@router.get("/{lote_id}/mtd", response_model=list[ec.PuntoMtd], summary="Serie del MTD por periodo")
async def serie_mtd(
    lote_id: int, actor: ActorDep, svc: Concepto, desde: date | None = None, hasta: date | None = None
) -> list[ec.PuntoMtd]:
    return await svc.serie_mtd(actor, lote_id, desde, hasta)


@router.get(
    "/{lote_id}/periodos", response_model=list[ec.PeriodoTrampeo], summary="Periodos de trampeo del lote"
)
async def periodos(lote_id: int, actor: ActorDep, svc: Concepto) -> list[ec.PeriodoTrampeo]:
    return await svc.periodos(actor, lote_id)


@router.get(
    "/{lote_id}/periodos/{peri_id}/mtd/versiones",
    response_model=list[ec.VersionMtd],
    summary="Recálculos del MTD de un periodo",
)
async def versiones_mtd(lote_id: int, peri_id: int, actor: ActorDep, svc: Concepto) -> list[ec.VersionMtd]:
    return await svc.versiones_mtd(actor, lote_id, peri_id)


@router.get(
    "/{lote_id}/conceptos",
    response_model=list[ec.Concepto],
    summary="Conceptos de aptitud emitidos (todas las versiones)",
)
async def conceptos(lote_id: int, actor: ActorDep, svc: Concepto) -> list[ec.Concepto]:
    return await svc.conceptos(actor, lote_id)


@router.get(
    "/{lote_id}/concepto", response_model=ec.ConceptoAFecha, summary="Concepto vigente a una fecha (RF-024)"
)
async def concepto_a_fecha(lote_id: int, actor: ActorDep, svc: Concepto, fecha: date) -> ec.ConceptoAFecha:
    return await svc.concepto_a_fecha(actor, lote_id, fecha)


@router.get(
    "/{lote_id}/etapa", response_model=ec.EtapaLote, summary="Etapa fenológica derivada y declarada (RN-012)"
)
async def etapa(lote_id: int, actor: ActorDep, svc: Concepto, fecha: date | None = None) -> ec.EtapaLote:
    return await svc.etapa(actor, lote_id, fecha)


@router.get("/{lote_id}/historial", response_model=Pagina[er.EntradaActividad], summary="Historial del lote")
async def historial(
    lote_id: int,
    actor: ActorDep,
    svc: Consulta,
    cursor: Cursor = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
) -> Pagina[er.EntradaActividad]:
    return await svc.actividad(actor, lote_id, None, None, desde, hasta, cursor)


@router.get(
    "/{lote_id}/actividad-reciente",
    response_model=list[er.ActividadReciente],
    summary="Actividad reciente del lote",
)
async def actividad_reciente(lote_id: int, actor: ActorDep, svc: Consulta) -> list[er.ActividadReciente]:
    return await svc.actividad_reciente(actor, lote_id)
