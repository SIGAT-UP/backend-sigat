"""Planificaciones (agrónomo -> productor) y actividades (agrónomo -> técnico)."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, status

from sigat_api.api.dependencias import requiere
from sigat_api.api.fabricas import servicio_planificacion
from sigat_api.api.v1.comunes import ERRORES, Cursor
from sigat_api.compartido.esquemas import Pagina
from sigat_api.compartido.tipos import Actor, EstadoPlanificacion
from sigat_api.modules.planificacion import esquemas as e
from sigat_api.modules.planificacion.servicio import ServicioPlanificacion

router = APIRouter(tags=["Planificación"], responses=ERRORES)
Svc = Annotated[ServicioPlanificacion, Depends(servicio_planificacion)]
Consulta = Annotated[Actor, Depends(requiere("planificacion.consultar"))]
Creador = Annotated[Actor, Depends(requiere("planificacion.crear"))]
Productor = Annotated[Actor, Depends(requiere("planificacion.responder"))]


@router.get("/planificaciones", response_model=Pagina[e.Planificacion], summary="Mis planificaciones")
async def listar(
    actor: Consulta,
    svc: Svc,
    cursor: Cursor = None,
    bandeja: Literal["recibidas", "creadas", "todas"] = "todas",
    estado: EstadoPlanificacion | None = None,
) -> Pagina[e.Planificacion]:
    return await svc.listar(actor, bandeja, estado, cursor)


@router.get(
    "/planificaciones/destinatarios",
    response_model=list[e.Destinatario],
    summary="A quién puedo dirigir una planificación",
)
async def destinatarios(
    actor: Creador, svc: Svc, tipo: Literal["productor", "tecnico"]
) -> list[e.Destinatario]:
    return await svc.destinatarios(actor, tipo)


@router.get(
    "/planificaciones/lotes-asignables",
    response_model=list[e.LoteAsignable],
    summary="Lotes que puedo asignar",
)
async def lotes_asignables(
    actor: Creador, svc: Svc, destinatario: int | None = None
) -> list[e.LoteAsignable]:
    return await svc.lotes_asignables(actor, destinatario)


@router.get(
    "/planificaciones/{plan_id}", response_model=e.PlanificacionDetalle, summary="Detalle de la planificación"
)
async def obtener(plan_id: UUID, actor: Consulta, svc: Svc) -> e.PlanificacionDetalle:
    return await svc.obtener(actor, plan_id)


@router.post(
    "/planificaciones",
    response_model=e.PlanificacionDetalle,
    status_code=status.HTTP_201_CREATED,
    summary="Crear planificación (productor) o actividad (técnico)",
)
async def crear(s: e.NuevaPlanificacion, actor: Creador, svc: Svc) -> e.PlanificacionDetalle:
    return await svc.crear(actor, s)


@router.post(
    "/planificaciones/{plan_id}/aceptacion",
    response_model=e.PlanificacionDetalle,
    summary="Aceptar (solo productor)",
)
async def aceptar(plan_id: UUID, s: e.Aceptacion, actor: Productor, svc: Svc) -> e.PlanificacionDetalle:
    return await svc.aceptar(actor, plan_id, s)


@router.post(
    "/planificaciones/{plan_id}/rechazo",
    response_model=e.PlanificacionDetalle,
    summary="Rechazar con motivo (solo productor)",
)
async def rechazar(plan_id: UUID, s: e.Rechazo, actor: Productor, svc: Svc) -> e.PlanificacionDetalle:
    return await svc.rechazar(actor, plan_id, s)


@router.post(
    "/planificaciones/{plan_id}/lotes/{lote_id}/resultado",
    response_model=e.PlanificacionDetalle,
    summary="Registrar el resultado de la actividad en un lote (solo técnico)",
)
async def resultado_lote(
    plan_id: UUID,
    lote_id: int,
    s: e.EntradaResultadoLote,
    actor: Annotated[Actor, Depends(requiere("planificacion.resultado_lote"))],
    svc: Svc,
) -> e.PlanificacionDetalle:
    return await svc.registrar_resultado_lote(actor, plan_id, lote_id, s)


@router.get(
    "/actividades-tecnico",
    response_model=Pagina[e.ActividadTecnico],
    summary="Informe de actividades de técnicos (realizadas y no realizadas)",
)
async def actividades(
    actor: Annotated[Actor, Depends(requiere("actividades_tecnico.consultar"))],
    svc: Svc,
    cursor: Cursor = None,
    usua_id: int | None = None,
    pred_id: int | None = None,
) -> Pagina[e.ActividadTecnico]:
    return await svc.actividades_tecnico(actor, usua_id, pred_id, cursor)
