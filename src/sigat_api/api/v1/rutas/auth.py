"""Autenticación. La web recibe el refresco en cookie HttpOnly; el móvil en el cuerpo."""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response, status

from sigat_api.api.dependencias import ActorDep, configuracion
from sigat_api.api.fabricas import servicio_autenticacion, servicio_autenticacion_actor
from sigat_api.api.v1.comunes import ERRORES, ERRORES_PUBLICOS
from sigat_api.compartido.esquemas import Aceptado
from sigat_api.compartido.tipos import Cliente
from sigat_api.config import Configuracion
from sigat_api.modules.identidad import esquemas as e
from sigat_api.modules.identidad.servicio import ResultadoSesion, ServicioAutenticacion

router = APIRouter(prefix="/auth", tags=["Autenticación"])
Auth = Annotated[ServicioAutenticacion, Depends(servicio_autenticacion)]
Cfg = Annotated[Configuracion, Depends(configuracion)]


def _ruta_cookie(cfg: Configuracion) -> str:
    return f"{cfg.prefijo_api}/auth"


def _poner_cookie(response: Response, cfg: Configuracion, r: ResultadoSesion, recordar: bool) -> None:
    """Web: el refresco viaja SOLO en cookie HttpOnly (JavaScript no la puede leer).
    Sin «recordar», la cookie es de sesión del navegador (se borra al cerrarlo)."""
    if r.cliente is not Cliente.WEB:
        return
    response.set_cookie(
        cfg.cookie_refresco_nombre,
        r.token_refresco,
        max_age=int(r.vida_refresco.total_seconds()) if recordar else None,
        path=_ruta_cookie(cfg),
        domain=cfg.cookie_dominio or None,
        secure=cfg.cookie_segura,
        httponly=True,
        samesite="strict",
    )


@router.post("/login", response_model=e.RespuestaLogin, responses=ERRORES_PUBLICOS, summary="Iniciar sesión")
async def login(
    s: e.SolicitudLogin, request: Request, response: Response, svc: Auth, cfg: Cfg
) -> e.RespuestaLogin:
    """Entra con **usuario o correo** y contraseña.

    * Web: ``cliente=web``; el refresco llega en la cookie ``sigat_refresco`` (HttpOnly).
    * Móvil: ``cliente=movil``; guardar ``token_refresco`` y ``disp_id`` en almacenamiento seguro
      y reenviar ``dispositivo.disp_id`` en los siguientes inicios de sesión.
    * Errores: 401 ``CREDENCIALES_INVALIDAS`` · 403 ``ROL_SOLO_MOVIL`` · 403 ``CUENTA_INCOMPLETA`` ·
      403 ``USAR_PROVEEDOR_INSTITUCIONAL`` · 403 ``REQUIERE_RESTABLECER`` · 429 ``LOGIN_BLOQUEADO``.
    """
    r = await svc.iniciar_sesion(s, request.client.host if request.client else None)
    _poner_cookie(response, cfg, r, s.recordar)
    return r.respuesta


@router.post(
    "/refresco",
    response_model=e.RespuestaLogin,
    responses=ERRORES_PUBLICOS,
    summary="Renovar el token de acceso",
)
async def refrescar(
    s: e.SolicitudRefresco,
    response: Response,
    svc: Auth,
    cfg: Cfg,
    sigat_refresco: Annotated[str | None, Cookie()] = None,
) -> e.RespuestaLogin:
    """Móvil: envía ``token_refresco``. Web: cuerpo vacío ``{}``; el refresco se lee de la cookie.
    El refresco ROTA: el anterior deja de servir (si se reutiliza, se cierra la sesión)."""
    r = await svc.refrescar(s.token_refresco or sigat_refresco or "")
    _poner_cookie(response, cfg, r, recordar=True)
    return r.respuesta


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, responses=ERRORES, summary="Cerrar sesión")
async def logout(
    actor: ActorDep,
    response: Response,
    cfg: Cfg,
    svc: ServicioAutenticacion = Depends(servicio_autenticacion_actor),
) -> None:
    await svc.cerrar_sesion(actor)
    response.delete_cookie(
        cfg.cookie_refresco_nombre,
        path=_ruta_cookie(cfg),
        domain=cfg.cookie_dominio or None,
        secure=cfg.cookie_segura,
        httponly=True,
        samesite="strict",
    )


@router.get(
    "/sesion", response_model=e.UsuarioSesion, responses=ERRORES, summary="Usuario de la sesión actual"
)
async def sesion(
    actor: ActorDep, svc: ServicioAutenticacion = Depends(servicio_autenticacion_actor)
) -> e.UsuarioSesion:
    return await svc.sesion_actual(actor)


@router.post(
    "/recuperacion",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=Aceptado,
    responses=ERRORES_PUBLICOS,
    summary="Solicitar el restablecimiento de la contraseña",
)
async def recuperacion(s: e.SolicitudRecuperacion, svc: Auth) -> Aceptado:
    """Siempre 202 con el mismo mensaje, exista o no la cuenta (no enumera cuentas)."""
    await svc.solicitar_recuperacion(s)
    return Aceptado(mensaje="Si la cuenta existe, la solicitud quedó registrada.")


@router.post(
    "/recuperacion/confirmar",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=ERRORES_PUBLICOS,
    summary="Fijar nueva contraseña con el token recibido",
)
async def confirmar_recuperacion(s: e.ConfirmacionRecuperacion, svc: Auth) -> None:
    await svc.confirmar_recuperacion(s)


@router.post(
    "/contrasena", status_code=status.HTTP_204_NO_CONTENT, responses=ERRORES, summary="Cambiar mi contraseña"
)
async def cambiar_contrasena(
    s: e.CambioContrasena, actor: ActorDep, svc: ServicioAutenticacion = Depends(servicio_autenticacion_actor)
) -> None:
    await svc.cambiar_contrasena(actor, s)
