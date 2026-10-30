"""Archivos (fotos, documentos) y evidencia. Subida en dos pasos con URL firmada."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse

from sigat_api.api.dependencias import ActorDep
from sigat_api.api.fabricas import servicio_archivos
from sigat_api.api.v1.comunes import ERRORES
from sigat_api.modules.imagenes import esquemas as e
from sigat_api.modules.imagenes.servicio import ServicioArchivos

router = APIRouter(tags=["Archivos y evidencia"], responses=ERRORES)
Svc = Annotated[ServicioArchivos, Depends(servicio_archivos)]


@router.post(
    "/archivos",
    response_model=e.RespuestaNuevoArchivo,
    status_code=status.HTTP_201_CREATED,
    summary="Paso 1: declarar el archivo y obtener la URL de subida",
)
async def declarar(s: e.NuevoArchivo, actor: ActorDep, svc: Svc) -> e.RespuestaNuevoArchivo:
    return await svc.declarar(actor, s)


@router.put(
    "/archivos/{arch_id}/contenido",
    response_model=e.Archivo,
    summary="Paso 2 (alternativo): subir el binario a través de la API",
)
async def subir(arch_id: UUID, request: Request, actor: ActorDep, svc: Svc) -> e.Archivo:
    """Cuerpo = bytes crudos; Content-Type = arch_mime declarado. Preferir la URL firmada del paso 1."""
    contenido = await request.body()
    return await svc.subir_contenido(actor, arch_id, contenido, request.headers.get("content-type", ""))


@router.post(
    "/archivos/{arch_id}/confirmacion",
    response_model=e.Archivo,
    summary="Paso 2: avisar que el PUT a la URL firmada terminó",
)
async def confirmar(arch_id: UUID, actor: ActorDep, svc: Svc) -> e.Archivo:
    return await svc.confirmar_subida(actor, arch_id)


@router.get("/archivos/{arch_id}", response_model=e.Archivo, summary="Metadatos del archivo")
async def obtener(arch_id: UUID, actor: ActorDep, svc: Svc) -> e.Archivo:
    return await svc.obtener(actor, arch_id)


@router.get(
    "/archivos/{arch_id}/contenido",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    response_class=RedirectResponse,
    summary="Descargar (redirige a una URL firmada corta)",
)
async def descargar(arch_id: UUID, actor: ActorDep, svc: Svc) -> RedirectResponse:
    enlace = await svc.enlace_descarga(actor, arch_id)
    return RedirectResponse(enlace.url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.post(
    "/evidencias",
    response_model=e.Evidencia,
    status_code=status.HTTP_201_CREATED,
    summary="Ligar una foto almacenada a su lectura/hallazgo/visita/actividad",
)
async def vincular(s: e.VinculoEvidencia, actor: ActorDep, svc: Svc) -> e.Evidencia:
    return await svc.vincular_evidencia(actor, s)
