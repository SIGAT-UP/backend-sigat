"""Catálogos de referencia y geografía DANE."""

from typing import Annotated

from fastapi import APIRouter, Depends

from sigat_api.api.dependencias import ActorDep, requiere
from sigat_api.api.fabricas import servicio_catalogo
from sigat_api.api.v1.comunes import ERRORES
from sigat_api.compartido.tipos import Actor
from sigat_api.modules.catalogo import esquemas as e
from sigat_api.modules.catalogo.servicio import ServicioCatalogo

router = APIRouter(tags=["Catálogos"], responses=ERRORES)
Svc = Annotated[ServicioCatalogo, Depends(servicio_catalogo)]


@router.get("/catalogos", response_model=list[e.CatalogoInfo], summary="Catálogos disponibles")
async def listar(actor: ActorDep, svc: Svc) -> list[e.CatalogoInfo]:
    return await svc.listar(actor)


@router.get("/catalogos/{codigo}", response_model=list[e.ItemCatalogo], summary="Valores de un catálogo")
async def items(
    codigo: str, actor: ActorDep, svc: Svc, incluir_inactivos: bool = False
) -> list[e.ItemCatalogo]:
    return await svc.items(actor, codigo, incluir_inactivos)


@router.put(
    "/catalogos/{codigo}",
    response_model=e.CatalogoInfo,
    summary="Reemplazar los valores de un catálogo editable",
)
async def reemplazar(
    codigo: str,
    s: e.ReemplazoCatalogo,
    actor: Annotated[Actor, Depends(requiere("catalogos.editar"))],
    svc: Svc,
) -> e.CatalogoInfo:
    return await svc.reemplazar(actor, codigo, s)


@router.get("/geografia/departamentos", response_model=list[e.Departamento], summary="Departamentos (DANE)")
async def departamentos(actor: ActorDep, svc: Svc) -> list[e.Departamento]:
    return await svc.departamentos()


@router.get("/geografia/municipios", response_model=list[e.Municipio], summary="Municipios (DANE, Divipola)")
async def municipios(actor: ActorDep, svc: Svc, depa_id: int | None = None) -> list[e.Municipio]:
    return await svc.municipios(depa_id)
