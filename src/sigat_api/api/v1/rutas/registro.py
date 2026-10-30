"""Registros de campo: visitas, lecturas, revisión del agrónomo, autorreportes y actividad."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, status

from sigat_api.api.dependencias import ActorDep, requiere
from sigat_api.api.fabricas import servicio_consulta_registro, servicio_registro, servicio_revision
from sigat_api.api.v1.comunes import ERRORES, Cursor
from sigat_api.compartido.esquemas import Pagina
from sigat_api.compartido.tipos import Actor, EstadoRevision, Linaje
from sigat_api.modules.registro import esquemas as e
from sigat_api.modules.registro.servicio import ServicioConsultaRegistro, ServicioRegistro, ServicioRevision

router = APIRouter(responses=ERRORES)
Consulta = Annotated[ServicioConsultaRegistro, Depends(servicio_consulta_registro)]
Registro = Annotated[ServicioRegistro, Depends(servicio_registro)]
Revision = Annotated[ServicioRevision, Depends(servicio_revision)]
Revisor = Annotated[Actor, Depends(requiere("revisiones.resolver"))]
Productor = Annotated[Actor, Depends(requiere("autorreporte.registrar"))]


# ------------------------------------------------------------------ visitas y lecturas
@router.get(
    "/visitas", tags=["Visitas y lecturas"], response_model=Pagina[e.Visita], summary="Visitas de inspección"
)
async def visitas(
    actor: Annotated[Actor, Depends(requiere("visitas.consultar"))],
    svc: Consulta,
    cursor: Cursor = None,
    pred_id: int | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
) -> Pagina[e.Visita]:
    return await svc.visitas(actor, pred_id, desde, hasta, cursor)


@router.get(
    "/visitas/{visi_id}",
    tags=["Visitas y lecturas"],
    response_model=e.VisitaDetalle,
    summary="Visita con sus lecturas",
)
async def visita(
    visi_id: UUID, actor: Annotated[Actor, Depends(requiere("visitas.consultar"))], svc: Consulta
) -> e.VisitaDetalle:
    return await svc.visita(actor, visi_id)


@router.get(
    "/lecturas", tags=["Visitas y lecturas"], response_model=Pagina[e.Lectura], summary="Lecturas vigentes"
)
async def lecturas(
    actor: Annotated[Actor, Depends(requiere("lecturas.consultar"))],
    svc: Consulta,
    cursor: Cursor = None,
    lote_id: int | None = None,
    tram_id: int | None = None,
    desde: datetime | None = None,
) -> Pagina[e.Lectura]:
    return await svc.lecturas(actor, lote_id, tram_id, desde, cursor)


@router.get(
    "/lecturas/{registro_id}/versiones",
    tags=["Visitas y lecturas"],
    response_model=e.HistorialVersiones,
    summary="Todas las versiones de una lectura (RF-052)",
)
async def versiones_lectura(
    registro_id: UUID, actor: Annotated[Actor, Depends(requiere("lecturas.consultar"))], svc: Consulta
) -> e.HistorialVersiones:
    return await svc.versiones_lectura(actor, registro_id)


@router.post(
    "/lecturas/{registro_id}/correcciones",
    tags=["Revisión"],
    response_model=e.Lectura,
    status_code=status.HTTP_201_CREATED,
    summary="Corregir especímenes (versión n+1)",
)
async def corregir_lectura(
    registro_id: UUID,
    s: e.CorreccionLectura,
    actor: Annotated[Actor, Depends(requiere("lecturas.corregir"))],
    svc: Registro,
) -> e.Lectura:
    return await svc.corregir_lectura(actor, registro_id, s)


@router.post(
    "/lecturas/{registro_id}/anulaciones",
    tags=["Revisión"],
    response_model=e.Lectura,
    status_code=status.HTTP_201_CREATED,
    summary="Rechazar/anular una lectura (versión n+1 anulada)",
)
async def anular_lectura(
    registro_id: UUID,
    s: e.AnulacionRegistro,
    actor: Annotated[Actor, Depends(requiere("lecturas.corregir"))],
    svc: Registro,
) -> e.Lectura:
    return await svc.anular_lectura(actor, registro_id, s)


# ------------------------------------------------------------------ revisión del agrónomo (sobre la visita)
@router.get(
    "/revisiones",
    tags=["Revisión"],
    response_model=Pagina[e.RegistroRevision],
    summary="Registros de campo por revisar",
)
async def revisiones(
    actor: Revisor, svc: Revision, cursor: Cursor = None, estado: EstadoRevision | None = None
) -> Pagina[e.RegistroRevision]:
    return await svc.listar(actor, estado, cursor)


@router.get(
    "/revisiones/{visi_id}",
    tags=["Revisión"],
    response_model=e.RevisionDetalle,
    summary="Detalle del registro en revisión",
)
async def revision(visi_id: UUID, actor: Revisor, svc: Revision) -> e.RevisionDetalle:
    return await svc.obtener(actor, visi_id)


@router.post(
    "/revisiones/{visi_id}/aceptacion",
    tags=["Revisión"],
    response_model=e.RevisionDetalle,
    summary="Aceptar el registro (visita)",
)
async def aceptar(visi_id: UUID, actor: Revisor, svc: Revision) -> e.RevisionDetalle:
    return await svc.aceptar(actor, visi_id)


@router.post(
    "/revisiones/{visi_id}/observacion",
    tags=["Revisión"],
    response_model=e.RevisionDetalle,
    summary="Pasar a 'en revisión' con motivo",
)
async def observar(
    visi_id: UUID, s: e.ObservacionRevision, actor: Revisor, svc: Revision
) -> e.RevisionDetalle:
    return await svc.marcar_en_revision(actor, visi_id, s)


# ------------------------------------------------------------------ autorreporte del productor (en línea)
@router.get(
    "/aplicaciones",
    tags=["Autorreporte"],
    response_model=Pagina[e.Aplicacion],
    summary="Aplicaciones fitosanitarias",
)
async def aplicaciones(
    actor: Annotated[Actor, Depends(requiere("autorreporte.consultar"))],
    svc: Consulta,
    cursor: Cursor = None,
    lote_id: int | None = None,
) -> Pagina[e.Aplicacion]:
    return await svc.aplicaciones(actor, lote_id, cursor)


@router.post(
    "/aplicaciones",
    tags=["Autorreporte"],
    response_model=e.Aplicacion,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar aplicación (idempotente por apli_registro_id)",
)
async def registrar_aplicacion(s: e.NuevaAplicacion, actor: Productor, svc: Registro) -> e.Aplicacion:
    return await svc.registrar_aplicacion(actor, s)


@router.post(
    "/aplicaciones/{registro_id}/versiones",
    tags=["Autorreporte"],
    response_model=e.Aplicacion,
    status_code=status.HTTP_201_CREATED,
    summary="Corregir o anular una aplicación",
)
async def version_aplicacion(
    registro_id: UUID, s: e.NuevaVersionAutorreporte, actor: Productor, svc: Registro
) -> e.Aplicacion:
    return await svc.nueva_version_aplicacion(actor, registro_id, s)


@router.get("/cosechas", tags=["Autorreporte"], response_model=Pagina[e.Cosecha], summary="Cosechas")
async def cosechas(
    actor: Annotated[Actor, Depends(requiere("autorreporte.consultar"))],
    svc: Consulta,
    cursor: Cursor = None,
    lote_id: int | None = None,
) -> Pagina[e.Cosecha]:
    return await svc.cosechas(actor, lote_id, cursor)


@router.post(
    "/cosechas",
    tags=["Autorreporte"],
    response_model=e.Cosecha,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar cosecha esperada/real",
)
async def registrar_cosecha(s: e.NuevaCosecha, actor: Productor, svc: Registro) -> e.Cosecha:
    return await svc.registrar_cosecha(actor, s)


@router.post(
    "/cosechas/{registro_id}/versiones",
    tags=["Autorreporte"],
    response_model=e.Cosecha,
    status_code=status.HTTP_201_CREATED,
    summary="Corregir o anular una cosecha (p. ej. añadir lo real)",
)
async def version_cosecha(
    registro_id: UUID, s: e.NuevaVersionAutorreporte, actor: Productor, svc: Registro
) -> e.Cosecha:
    return await svc.nueva_version_cosecha(actor, registro_id, s)


# ------------------------------------------------------------------ historial unificado
@router.get(
    "/actividad",
    tags=["Historial"],
    response_model=Pagina[e.EntradaActividad],
    summary="Historial de actividad de mis lotes (visitas, aplicaciones, cosechas, correcciones)",
)
async def actividad(
    actor: ActorDep,
    svc: Consulta,
    cursor: Cursor = None,
    lote_id: int | None = None,
    tipo: Literal["vigilancia", "aplicacion", "cosecha", "correccion", "hallazgo", "etapa"] | None = None,
    linaje: Linaje | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
) -> Pagina[e.EntradaActividad]:
    return await svc.actividad(actor, lote_id, tipo, linaje, desde, hasta, cursor)
