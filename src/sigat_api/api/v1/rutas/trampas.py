"""Trampas y su ubicación/asignación al lote."""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, status

from sigat_api.api.dependencias import ActorDep, requiere
from sigat_api.api.fabricas import servicio_trampas
from sigat_api.api.v1.comunes import ERRORES
from sigat_api.compartido.tipos import Actor
from sigat_api.modules.configuracion import esquemas as e
from sigat_api.modules.configuracion.servicio import ServicioTrampas

router = APIRouter(prefix="/trampas", tags=["Trampas"], responses=ERRORES)
Svc = Annotated[ServicioTrampas, Depends(servicio_trampas)]
Editor = Annotated[Actor, Depends(requiere("trampas.editar"))]


@router.get("", response_model=list[e.Trampa], summary="Trampas visibles (por lote o predio)")
async def listar(
    actor: ActorDep, svc: Svc, lote_id: int | None = None, pred_id: int | None = None
) -> list[e.Trampa]:
    return await svc.listar(actor, lote_id, pred_id)


@router.get(
    "/codigo/{tram_codigo}", response_model=e.BusquedaTrampa, summary="Buscar por código ICA (QR o digitado)"
)
async def por_codigo(
    tram_codigo: str,
    actor: ActorDep,
    svc: Svc,
    lote_activo: int | None = None,
    lat: Decimal | None = None,
    lng: Decimal | None = None,
) -> e.BusquedaTrampa:
    """En campo el móvil usa su base local; este endpoint sirve en línea (y a la web)."""
    return await svc.buscar_por_codigo(actor, tram_codigo, lote_activo, lat, lng)


@router.get("/{tram_id}", response_model=e.Trampa, summary="Detalle de la trampa")
async def obtener(tram_id: int, actor: ActorDep, svc: Svc) -> e.Trampa:
    return await svc.obtener(actor, tram_id)


@router.post(
    "", response_model=e.Trampa, status_code=status.HTTP_201_CREATED, summary="Crear trampa con su ubicación"
)
async def crear(s: e.NuevaTrampa, actor: Editor, svc: Svc) -> e.Trampa:
    return await svc.crear(actor, s)


@router.patch("/{tram_id}", response_model=e.Trampa, summary="Actualizar trampa (estado, atrayente)")
async def actualizar(tram_id: int, s: e.ActualizacionTrampa, actor: Editor, svc: Svc) -> e.Trampa:
    return await svc.actualizar(actor, tram_id, s)


@router.get(
    "/{tram_id}/ubicaciones", response_model=list[e.UbicacionTrampa], summary="Historial de ubicaciones"
)
async def ubicaciones(tram_id: int, actor: ActorDep, svc: Svc) -> list[e.UbicacionTrampa]:
    return await svc.ubicaciones(actor, tram_id)


@router.post(
    "/{tram_id}/ubicaciones",
    response_model=e.UbicacionTrampa,
    status_code=status.HTTP_201_CREATED,
    summary="Reubicar o reasignar la trampa (cierra la ubicación vigente)",
)
async def reubicar(tram_id: int, s: e.NuevaUbicacion, actor: Editor, svc: Svc) -> e.UbicacionTrampa:
    return await svc.reubicar(actor, tram_id, s)
