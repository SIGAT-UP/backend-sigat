"""Contrato HTTP del módulo de identidad."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import EmailStr, Field, SecretStr, model_validator

from sigat_api.compartido.esquemas import Esquema
from sigat_api.compartido.tipos import Cliente, Plataforma, RolCodigo


# ------------------------------------------------------------------ autenticación
class DispositivoEntrada(Esquema):
    """Dispositivo desde el que se inicia sesión. El móvil reenvía su ``disp_id``
    guardado; la primera vez lo omite y el servidor lo crea. La web envía ``otro``."""

    disp_id: UUID | None = None
    plataforma: Plataforma = Plataforma.OTRO
    version_app: str | None = Field(None, max_length=40)
    nombre: str | None = Field(None, max_length=80)


class SolicitudLogin(Esquema):
    usuario: str = Field(
        ...,
        min_length=3,
        max_length=254,
        description="Nombre de usuario o correo (sin distinguir mayúsculas).",
    )
    contrasena: SecretStr = Field(..., min_length=1, max_length=256)
    cliente: Cliente = Field(..., description="web | movil. El rol Técnico solo puede entrar con movil.")
    recordar: bool = Field(False, description="Web: conservar la sesión al cerrar el navegador.")
    dispositivo: DispositivoEntrada | None = Field(
        None, description="Opcional. Si falta, se registra un dispositivo 'otro' (web)."
    )


class UsuarioSesion(Esquema):
    """Forma que leen ``UserSession.fromApi`` (móvil) y ``SessionUser`` (web)."""

    id: int = Field(..., description="usuario.usua_id")
    nombre: str = Field(..., description="persona.pers_nombre + pers_apellido")
    iniciales: str
    usuario: str = Field(..., description="usuario.usua_usuario")
    correo: str | None
    rol: RolCodigo
    rol_descripcion: str
    predio_etiqueta: str | None = Field(None, description="Productor: 'Finca X · durazno'.")
    requiere_cambio_contrasena: bool = False


class RespuestaLogin(Esquema):
    """``token`` y ``user`` conservan esos nombres por compatibilidad con
    ``UserSession.fromApi`` del móvil."""

    token: str = Field(..., description="JWT de acceso. Enviar como 'Authorization: Bearer <token>'.")
    tipo_token: Literal["Bearer"] = "Bearer"  # noqa: S105
    expira_en: int = Field(..., description="Segundos de vida del token de acceso.")
    token_refresco: str | None = Field(
        None, description="Solo cliente=movil. En web viaja en cookie HttpOnly y aquí es null."
    )
    disp_id: UUID = Field(
        ..., description="Dispositivo registrado. El cliente lo guarda y lo reenvía al entrar."
    )
    user: UsuarioSesion


class SolicitudRefresco(Esquema):
    token_refresco: str | None = Field(None, description="Móvil. La web lo omite: se lee de la cookie.")


class SolicitudRecuperacion(Esquema):
    identificador: str = Field(
        ..., min_length=3, max_length=254, description="Usuario o correo de la cuenta."
    )


class ConfirmacionRecuperacion(Esquema):
    token: str = Field(..., min_length=20, max_length=200)
    nueva_contrasena: SecretStr = Field(..., min_length=10, max_length=256)


class CambioContrasena(Esquema):
    actual: SecretStr
    nueva: SecretStr = Field(..., min_length=10, max_length=256)


# ------------------------------------------------------------------ perfil propio
class FotoPerfilEntrada(Esquema):
    arch_id: UUID = Field(..., description="Archivo de clase foto_perfil ya subido por /archivos.")


class PerfilPropio(Esquema):
    usua_id: int
    nombre: str
    usuario: str
    correo: str | None
    telefono: str | None
    rol: RolCodigo
    rol_descripcion: str
    foto_arch_id: UUID | None
    foto_url: str | None = Field(None, description="URL firmada temporal de la foto.")
    actualizado_en: datetime | None


class PredioAccesible(Esquema):
    """Fila de ``v_acceso_predio`` enriquecida."""

    pred_id: int
    pred_nombre: str
    origen: Literal["asignacion", "propietario", "global"]


# ------------------------------------------------------------------ administración de usuarios
class Rol(Esquema):
    rol_id: int
    rol_codigo: RolCodigo
    rol_descripcion: str
    rol_ambito: Literal["global", "predio"]


class UsuarioAdmin(Esquema):
    """Fila de ``v_usuario_admin`` (BD v9): solo usuarios vigentes (no eliminados)."""

    usua_id: int
    pers_cc: int
    nombre: str = Field(..., description="persona.pers_nombre")
    apellido: str = Field(..., description="persona.pers_apellido")
    nombre_completo: str
    iniciales: str
    correo: str | None
    telefono: str | None
    direccion: str | None
    usuario: str
    rol: RolCodigo
    rol_descripcion: str
    acceso: Literal["solo_movil", "web_y_movil"] = Field(..., description="TECNICO = solo_movil.")
    activo: bool
    proveedor: Literal["local", "externo"]
    ultimo_acceso: datetime | None
    requiere_cambio_contrasena: bool
    cent_id: int | None = Field(None, description="Centro de acopio (técnico y administrador).")
    tecn_codigo: str | None = None
    muni_id: int | None = Field(None, description="Municipio (productor).")
    predios: int = Field(0, description="Predios asignados vigentes.")


class DatosRolEntrada(Esquema):
    """Filas hijas que exige la BD según el rol: técnico y administrador -> centro de acopio;
    productor -> municipio. El agrónomo no tiene fila hija."""

    cent_id: int | None = Field(None, description="Centro de acopio (técnico y administrador).")
    tecn_codigo: str | None = Field(
        None, pattern=r"^[0-9]{8}$", description="Técnico: Divipola (5) + consecutivo (3)."
    )
    muni_id: int | None = Field(None, description="Productor: municipio.")


def _exigir_datos_rol(rol: RolCodigo, datos: DatosRolEntrada) -> None:
    """Mismas exigencias que las tablas tecnico, administrador y productor (BD v9)."""
    if rol in (RolCodigo.TECNICO, RolCodigo.ADMINISTRADOR) and datos.cent_id is None:
        raise ValueError("El técnico y el administrador necesitan centro de acopio (datos_rol.cent_id).")
    if rol is RolCodigo.PRODUCTOR and datos.muni_id is None:
        raise ValueError("El productor necesita municipio (datos_rol.muni_id).")


class NuevoUsuario(Esquema):
    pers_cc: int = Field(..., gt=0, lt=10**15, description="Cédula (persona.pers_cc), solo dígitos.")
    nombre: str = Field(..., min_length=1, max_length=120)
    apellido: str = Field(..., min_length=1, max_length=120)
    correo: EmailStr | None = None
    telefono: str | None = Field(None, pattern=r"^\+?[0-9]{7,15}$")
    direccion: str | None = Field(None, max_length=200)
    usuario: str = Field(
        ..., pattern=r"^[A-Za-z0-9._@-]{3,64}$", description="Único sin distinguir mayúsculas."
    )
    rol: RolCodigo
    proveedor: Literal["local", "externo"] = "local"
    sujeto_externo: str | None = None
    contrasena_temporal: SecretStr | None = Field(
        None,
        min_length=10,
        description="Contraseña inicial que el administrador entrega a la persona. Si se omite, la "
        "cuenta queda sin contraseña (usua_requiere_reinicio = true) hasta que el administrador le "
        "asigne una con POST /usuarios/{usua_id}/restablecimiento-contrasena.",
    )
    datos_rol: DatosRolEntrada = Field(default_factory=DatosRolEntrada)

    @model_validator(mode="after")
    def _coherencia(self) -> "NuevoUsuario":
        _exigir_datos_rol(self.rol, self.datos_rol)
        if self.proveedor == "externo" and (not self.sujeto_externo or self.contrasena_temporal is not None):
            raise ValueError("Una cuenta externa exige sujeto_externo y no lleva contraseña.")
        return self


class ActualizacionUsuario(Esquema):
    """Edición del administrador. Solo se cambian los campos enviados (PATCH).

    * ``pers_cc`` corrige una cédula mal digitada: la BD lo permite solo si ningún predio o
      registro depende de la persona (``fn_corregir_cedula``); si no, 409 ``CEDULA_EN_USO``.
    * Cambiar ``rol`` exige ``datos_rol`` del rol nuevo y revoca las sesiones del usuario.
    """

    pers_cc: int | None = Field(None, gt=0, lt=10**15)
    nombre: str | None = Field(None, min_length=1, max_length=120)
    apellido: str | None = Field(None, min_length=1, max_length=120)
    correo: EmailStr | None = None
    telefono: str | None = Field(None, pattern=r"^\+?[0-9]{7,15}$")
    direccion: str | None = Field(None, max_length=200)
    usuario: str | None = Field(None, pattern=r"^[A-Za-z0-9._@-]{3,64}$")
    rol: RolCodigo | None = None
    datos_rol: DatosRolEntrada | None = None

    @model_validator(mode="after")
    def _coherencia(self) -> "ActualizacionUsuario":
        if not self.model_fields_set:
            raise ValueError("Envíe al menos un campo para actualizar.")
        if self.rol is not None:
            _exigir_datos_rol(self.rol, self.datos_rol or DatosRolEntrada())
        return self


class EliminacionUsuario(Esquema):
    motivo: str = Field(
        ..., min_length=10, max_length=300, description="Queda en usua_motivo_eliminacion y en la bitácora."
    )


class VistaPreviaEliminacion(Esquema):
    """Qué pasará ANTES de confirmar (``fn_usuario_tiene_actividad``)."""

    usua_id: int
    tiene_actividad: bool
    resultado_esperado: Literal["eliminado", "dado_de_baja"]
    explicacion: str


class ResultadoEliminacion(Esquema):
    usua_id: int
    resultado: Literal["eliminado", "dado_de_baja"] = Field(
        ...,
        description="eliminado = borrado físico (no tenía actividad); dado_de_baja = baja definitiva que conserva la historia.",
    )
    mensaje: str


class AsignacionContrasena(Esquema):
    """El ADMINISTRADOR asigna una contraseña nueva (p. ej. tras una solicitud de
    «¿Problemas para ingresar?») y se la entrega a la persona por el medio que él elija.
    El backend nunca la devuelve ni la envía."""

    nueva_contrasena: SecretStr = Field(..., min_length=10, max_length=256)
    exigir_cambio: bool = Field(
        True,
        description="Marca usua_requiere_reinicio: la sesión trae requiere_cambio_contrasena = true "
        "para que la persona la cambie al entrar.",
    )


class ActivacionUsuario(Esquema):
    activo: bool
    motivo: str | None = Field(None, max_length=300)


class NuevaAsignacionPredio(Esquema):
    pred_id: int
    desde: date
    hasta: date | None = Field(None, description="Exclusivo. Nulo = vigente.")


class AsignacionPredio(Esquema):
    usup_id: int
    usua_id: int
    pred_id: int
    pred_nombre: str
    desde: date
    hasta: date | None
    asignado_por: int | None
