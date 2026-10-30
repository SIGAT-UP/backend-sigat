"""Vistas propias del productor."""

from typing import Annotated

from fastapi import APIRouter, Depends

from sigat_api.api.dependencias import requiere
from sigat_api.api.fabricas import servicio_concepto
from sigat_api.api.v1.comunes import ERRORES
from sigat_api.compartido.tipos import Actor
from sigat_api.modules.concepto import esquemas as e
from sigat_api.modules.concepto.servicio import ServicioConcepto

router = APIRouter(prefix="/productor", tags=["Productor"], responses=ERRORES)


@router.get("/cultivo", response_model=e.CultivoProductor, summary="Estado de mi cultivo (todos mis lotes)")
async def cultivo(
    actor: Annotated[Actor, Depends(requiere("autorreporte.registrar"))],
    svc: Annotated[ServicioConcepto, Depends(servicio_concepto)],
) -> e.CultivoProductor:
    return await svc.cultivo_productor(actor)
