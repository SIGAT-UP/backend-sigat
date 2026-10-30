"""Sincronización del móvil (Arquitectura §7.1)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from sigat_api.api.dependencias import requiere
from sigat_api.api.fabricas import servicio_sincronizacion
from sigat_api.api.v1.comunes import ERRORES, Limite
from sigat_api.compartido.tipos import Actor, ClasificacionOperacion
from sigat_api.modules.sincronizacion import esquemas as e
from sigat_api.modules.sincronizacion.servicio import ServicioSincronizacion

router = APIRouter(prefix="/sincronizacion", tags=["Sincronización"], responses=ERRORES)
Svc = Annotated[ServicioSincronizacion, Depends(servicio_sincronizacion)]
Emisor = Annotated[Actor, Depends(requiere("sincronizacion.enviar"))]


@router.post("/lotes", response_model=e.RespuestaLote, summary="Enviar un lote de operaciones idempotentes")
async def enviar_lote(s: e.LoteSincronizacion, actor: Emisor, svc: Svc) -> e.RespuestaLote:
    """Siempre 200 si el lote se pudo leer: el resultado de CADA operación va en ``resultados``.
    403 solo si el disp_id no es el del token o el dispositivo está dado de baja."""
    return await svc.recibir(actor, s)


@router.get(
    "/operaciones",
    response_model=list[e.OperacionPendiente],
    summary="Mis operaciones en 'revisar' o 'rechazada'",
)
async def pendientes(
    actor: Emisor,
    svc: Svc,
    clasificacion: Annotated[list[ClasificacionOperacion], Query()] = [  # noqa: B006
        ClasificacionOperacion.REVISAR,
        ClasificacionOperacion.RECHAZADA,
    ],
) -> list[e.OperacionPendiente]:
    return await svc.pendientes(actor, clasificacion)


@router.post(
    "/operaciones/{oper_id}/resolucion",
    response_model=e.ResultadoOperacion,
    summary="Confirmar o descartar una operación en 'revisar' (R-T5)",
)
async def resolver(oper_id: int, s: e.ResolucionOperacion, actor: Emisor, svc: Svc) -> e.ResultadoOperacion:
    return await svc.resolver(actor, oper_id, s)


@router.get("/cambios", response_model=e.Cambios, summary="Cambios del servidor desde un cursor (bajada)")
async def cambios(
    actor: Annotated[Actor, Depends(requiere("paquete_campo.descargar"))],
    svc: Svc,
    desde: str | None = None,
    limite: Limite = 100,
) -> e.Cambios:
    return await svc.cambios(actor, desde, limite)
