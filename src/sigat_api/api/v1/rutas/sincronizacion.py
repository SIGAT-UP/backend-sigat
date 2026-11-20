from typing import Annotated

from fastapi import APIRouter, Depends, status

from sigat_api.api.dependencias import requiere
from sigat_api.api.fabricas import servicio_sincronizacion
from sigat_api.api.v1.comunes import ERRORES
from sigat_api.compartido.tipos import Actor
from sigat_api.modules.sincronizacion import esquemas as e
from sigat_api.modules.sincronizacion.servicio import ServicioSincronizacion

router = APIRouter(prefix="/sincronizacion", tags=["Sincronización"], responses=ERRORES)
Svc = Annotated[ServicioSincronizacion, Depends(servicio_sincronizacion)]
Emisor = Annotated[Actor, Depends(requiere("sincronizacion.enviar"))]


@router.post(
    "/lotes",
    response_model=e.RespuestaLote,
    status_code=status.HTTP_207_MULTI_STATUS,
    summary="Enviar un lote de operaciones idempotentes",
)
async def enviar_lote(s: e.LoteSincronizacion, actor: Emisor, svc: Svc) -> e.RespuestaLote:
    """207 Multi-Status siempre que el lote se pudo leer, se acepten todas, algunas o ninguna de sus
    operaciones: el resultado de CADA una va en ``resultados``. El lote completo se rechaza solo con
    401 (sin sesión), 403 (disp_id distinto al del token o dispositivo dado de baja) o 422 (cuerpo inválido)."""
    return await svc.recibir(actor, s)


@router.get(
    "/operaciones",
    response_model=list[e.OperacionPendiente],
    summary="Consultar las operaciones recibidas y su resultado",
)
async def operaciones(actor: Emisor, svc: Svc) -> list[e.OperacionPendiente]:
    return await svc.pendientes(actor)
