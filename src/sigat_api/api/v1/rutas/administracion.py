"""Administración: usuarios, roles, asignación de predios, auditoría y panel. Solo ADMINISTRADOR."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from sigat_api.api.dependencias import requiere
from sigat_api.api.fabricas import servicio_auditoria, servicio_usuarios
from sigat_api.api.v1 import esquemas_compuestos as c
from sigat_api.api.v1.comunes import ERRORES, Cursor
from sigat_api.compartido.errores import NoImplementado
from sigat_api.compartido.esquemas import Pagina
from sigat_api.compartido.tipos import Actor, RolCodigo
from sigat_api.modules.auditoria import esquemas as ea
from sigat_api.modules.auditoria.servicio import ServicioAuditoria
from sigat_api.modules.identidad import esquemas as e
from sigat_api.modules.identidad.servicio import ServicioUsuarios

router = APIRouter(tags=["Administración"], responses=ERRORES)
Admin = Annotated[Actor, Depends(requiere("usuarios.administrar"))]
Usuarios = Annotated[ServicioUsuarios, Depends(servicio_usuarios)]


@router.get("/admin/resumen", response_model=c.ResumenAdministracion, summary="Panel del administrador")
async def resumen(actor: Admin) -> c.ResumenAdministracion:
    """Compone identidad (usuarios/roles), configuración (trampas/predios/programa) y auditoría."""
    raise NoImplementado("Panel del administrador")


@router.get("/roles", response_model=list[e.Rol], summary="Roles del sistema")
async def roles(actor: Admin, svc: Usuarios) -> list[e.Rol]:
    return await svc.roles()


@router.get("/usuarios", response_model=Pagina[e.UsuarioAdmin], summary="Usuarios")
async def listar(
    actor: Admin,
    svc: Usuarios,
    cursor: Cursor = None,
    rol: RolCodigo | None = None,
    activo: bool | None = None,
) -> Pagina[e.UsuarioAdmin]:
    return await svc.listar(actor, rol, activo, cursor)


@router.post(
    "/usuarios", response_model=e.UsuarioAdmin, status_code=status.HTTP_201_CREATED, summary="Crear usuario"
)
async def crear(s: e.NuevoUsuario, actor: Admin, svc: Usuarios) -> e.UsuarioAdmin:
    return await svc.crear(actor, s)


@router.get("/usuarios/{usua_id}", response_model=e.UsuarioAdmin, summary="Detalle de usuario")
async def obtener(usua_id: int, actor: Admin, svc: Usuarios) -> e.UsuarioAdmin:
    return await svc.obtener(actor, usua_id)


@router.patch(
    "/usuarios/{usua_id}",
    response_model=e.UsuarioAdmin,
    summary="Editar usuario (nombre, correo, teléfono, usuario, rol, cédula)",
)
async def actualizar(usua_id: int, s: e.ActualizacionUsuario, actor: Admin, svc: Usuarios) -> e.UsuarioAdmin:
    return await svc.actualizar(actor, usua_id, s)


@router.get(
    "/usuarios/{usua_id}/eliminacion",
    response_model=e.VistaPreviaEliminacion,
    summary="Antes de eliminar: ¿se borrará o se dará de baja?",
)
async def vista_previa_eliminacion(usua_id: int, actor: Admin, svc: Usuarios) -> e.VistaPreviaEliminacion:
    return await svc.vista_previa_eliminacion(actor, usua_id)


@router.post(
    "/usuarios/{usua_id}/eliminacion",
    response_model=e.ResultadoEliminacion,
    summary="Eliminar usuario (borra si no tiene actividad; si la tiene, baja definitiva)",
)
async def eliminar(
    usua_id: int, s: e.EliminacionUsuario, actor: Admin, svc: Usuarios
) -> e.ResultadoEliminacion:
    """POST con cuerpo (y no DELETE) porque la eliminación exige motivo y su resultado varía."""
    return await svc.eliminar(actor, usua_id, s)


@router.post(
    "/usuarios/{usua_id}/activacion", response_model=e.UsuarioAdmin, summary="Activar o desactivar usuario"
)
async def activar(usua_id: int, s: e.ActivacionUsuario, actor: Admin, svc: Usuarios) -> e.UsuarioAdmin:
    return await svc.activar(actor, usua_id, s)


@router.post(
    "/usuarios/{usua_id}/restablecimiento-contrasena",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Asignar una contraseña nueva (el administrador se la entrega a la persona)",
)
async def restablecer(usua_id: int, s: e.AsignacionContrasena, actor: Admin, svc: Usuarios) -> None:
    """Respuesta al aviso «Solicitud de nueva contraseña» (o cuando el administrador lo decida).
    Cierra todas las sesiones de esa persona y marca atendidas sus solicitudes pendientes.
    La contraseña no se devuelve ni se envía por el sistema."""
    await svc.asignar_contrasena(actor, usua_id, s)


@router.get(
    "/usuarios/{usua_id}/predios", response_model=list[e.AsignacionPredio], summary="Predios asignados"
)
async def asignaciones(usua_id: int, actor: Admin, svc: Usuarios) -> list[e.AsignacionPredio]:
    return await svc.asignaciones(actor, usua_id)


@router.post(
    "/usuarios/{usua_id}/predios",
    response_model=e.AsignacionPredio,
    status_code=status.HTTP_201_CREATED,
    summary="Asignar predio",
)
async def asignar(
    usua_id: int, s: e.NuevaAsignacionPredio, actor: Admin, svc: Usuarios
) -> e.AsignacionPredio:
    return await svc.asignar_predio(actor, usua_id, s)


@router.delete(
    "/usuarios/{usua_id}/predios/{usup_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cerrar asignación (no borra: fija la fecha de fin)",
)
async def cerrar_asignacion(usua_id: int, usup_id: int, actor: Admin, svc: Usuarios) -> None:
    await svc.cerrar_asignacion(actor, usua_id, usup_id)


@router.get(
    "/auditoria", response_model=Pagina[ea.EntradaAuditoria], summary="Bitácora de auditoría (RF-083)"
)
async def auditoria(
    actor: Annotated[Actor, Depends(requiere("auditoria.consultar"))],
    svc: Annotated[ServicioAuditoria, Depends(servicio_auditoria)],
    cursor: Cursor = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    categoria: ea.CategoriaAuditoria | None = None,
    usua_id: int | None = None,
    con_detalle: Annotated[bool, Query()] = False,
) -> Pagina[ea.EntradaAuditoria]:
    return await svc.listar(actor, desde, hasta, categoria, usua_id, con_detalle, cursor)
