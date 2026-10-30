"""Predios: datos, cartografía, programa de inspección, retícula y paquete de campo."""

from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response, status

from sigat_api.api.dependencias import ActorDep, requiere
from sigat_api.api.fabricas import (
    servicio_lotes,
    servicio_paquete,
    servicio_predios,
    servicio_programa,
    servicio_reticula,
)
from sigat_api.api.v1.comunes import ERRORES
from sigat_api.compartido.tipos import Actor
from sigat_api.modules.configuracion import esquemas as e
from sigat_api.modules.configuracion.servicio import (
    ServicioLotes,
    ServicioPaqueteCampo,
    ServicioPredios,
    ServicioPrograma,
    ServicioReticula,
)

router = APIRouter(prefix="/predios", tags=["Predios"], responses=ERRORES)
Predios = Annotated[ServicioPredios, Depends(servicio_predios)]


@router.get("", response_model=list[e.Predio], summary="Predios visibles para mí")
async def listar(actor: ActorDep, svc: Predios) -> list[e.Predio]:
    return await svc.listar(actor)


@router.get("/{pred_id}", response_model=e.Predio, summary="Detalle del predio")
async def obtener(pred_id: int, actor: ActorDep, svc: Predios) -> e.Predio:
    return await svc.obtener(actor, pred_id)


@router.patch("/{pred_id}", response_model=e.Predio, summary="Actualizar predio (cartografía)")
async def actualizar(
    pred_id: int,
    s: e.ActualizacionPredio,
    actor: Annotated[Actor, Depends(requiere("predios.editar"))],
    svc: Predios,
) -> e.Predio:
    return await svc.actualizar(actor, pred_id, s)


@router.put("/{pred_id}/geometria", response_model=e.Predio, summary="Fijar el límite del predio")
async def geometria(
    pred_id: int,
    s: e.EntradaGeometria,
    actor: Annotated[Actor, Depends(requiere("predios.editar"))],
    svc: Predios,
) -> e.Predio:
    return await svc.poner_geometria(actor, pred_id, s)


@router.get("/{pred_id}/mapa", response_model=e.MapaPredio, summary="Capas GeoJSON del predio para MapLibre")
async def mapa(pred_id: int, actor: ActorDep, svc: Predios, instante: datetime | None = None) -> e.MapaPredio:
    return await svc.mapa(actor, pred_id, instante)


@router.post(
    "/{pred_id}/lotes",
    response_model=e.LoteDetalle,
    status_code=status.HTTP_201_CREATED,
    summary="Crear lote",
)
async def crear_lote(
    pred_id: int,
    s: e.NuevoLote,
    actor: Annotated[Actor, Depends(requiere("lotes.editar"))],
    svc: Annotated[ServicioLotes, Depends(servicio_lotes)],
) -> e.LoteDetalle:
    return await svc.crear(actor, pred_id, s)


@router.get(
    "/{pred_id}/programa",
    response_model=e.ProgramaInspeccion,
    summary="Programa de inspección vigente (o a una fecha)",
)
async def programa(
    pred_id: int,
    actor: ActorDep,
    svc: Annotated[ServicioPrograma, Depends(servicio_programa)],
    fecha: date | None = None,
) -> e.ProgramaInspeccion:
    return await svc.vigente(actor, pred_id, fecha)


@router.get(
    "/{pred_id}/programa/versiones",
    response_model=list[e.ProgramaInspeccion],
    summary="Historial de versiones del programa",
)
async def versiones_programa(
    pred_id: int, actor: ActorDep, svc: Annotated[ServicioPrograma, Depends(servicio_programa)]
) -> list[e.ProgramaInspeccion]:
    return await svc.versiones(actor, pred_id)


@router.post(
    "/{pred_id}/programa/versiones",
    response_model=e.ProgramaInspeccion,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nueva versión del programa (ADR-05)",
)
async def nueva_version_programa(
    pred_id: int,
    s: e.NuevaVersionPrograma,
    actor: Annotated[Actor, Depends(requiere("programa.versionar"))],
    svc: Annotated[ServicioPrograma, Depends(servicio_programa)],
) -> e.ProgramaInspeccion:
    return await svc.nueva_version(actor, pred_id, s)


@router.get("/{pred_id}/reticula", response_model=e.Reticula, summary="Retícula del predio")
async def reticula(
    pred_id: int, actor: ActorDep, svc: Annotated[ServicioReticula, Depends(servicio_reticula)]
) -> e.Reticula:
    return await svc.obtener(actor, pred_id)


@router.post(
    "/{pred_id}/reticulas",
    response_model=e.Reticula,
    status_code=status.HTTP_201_CREATED,
    summary="Crear retícula",
)
async def crear_reticula(
    pred_id: int,
    s: e.NuevaReticula,
    actor: Annotated[Actor, Depends(requiere("reticula.crear"))],
    svc: Annotated[ServicioReticula, Depends(servicio_reticula)],
) -> e.Reticula:
    return await svc.crear(actor, pred_id, s)


@router.get(
    "/{pred_id}/paquete-campo",
    response_model=e.PaqueteCampoInfo,
    summary="Versión vigente del paquete de campo",
)
async def paquete_info(
    pred_id: int,
    actor: Annotated[Actor, Depends(requiere("paquete_campo.descargar"))],
    svc: Annotated[ServicioPaqueteCampo, Depends(servicio_paquete)],
) -> e.PaqueteCampoInfo:
    return await svc.info(actor, pred_id)


@router.get(
    "/{pred_id}/paquete-campo/contenido",
    response_model=e.PaqueteCampoContenido,
    responses={304: {"description": "El paquete del dispositivo ya es el vigente (If-None-Match)."}},
    summary="Descargar el paquete de campo (ADR-09)",
)
async def paquete_contenido(
    pred_id: int,
    response: Response,
    actor: Annotated[Actor, Depends(requiere("paquete_campo.descargar"))],
    svc: Annotated[ServicioPaqueteCampo, Depends(servicio_paquete)],
    if_none_match: Annotated[str | None, Header()] = None,
) -> e.PaqueteCampoContenido | Response:
    contenido = await svc.contenido(actor, pred_id, if_none_match)
    if contenido is None:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED)
    response.headers["ETag"] = f'"{contenido.paqu_hash}"'
    return contenido
