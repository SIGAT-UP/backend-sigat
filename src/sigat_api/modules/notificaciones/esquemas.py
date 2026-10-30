"""Contrato HTTP de notificaciones (móvil ``NotificationsRepository``, web ``NotificationRepository``)."""

from datetime import datetime

from pydantic import Field

from sigat_api.compartido.esquemas import Esquema
from sigat_api.compartido.tipos import CategoriaNotificacion


class DestinoNotificacion(Esquema):
    ruta: str = Field(..., description="noti_destino_ruta: pantalla a abrir (cada front la traduce).")
    argumento: str | None


class Notificacion(Esquema):
    noti_id: int
    categoria: CategoriaNotificacion
    titulo: str
    cuerpo: str
    creada_en: datetime
    leida_en: datetime | None
    leida: bool
    destino: DestinoNotificacion | None


class ConteoNoLeidas(Esquema):
    no_leidas: int


class PreferenciasNotificacion(Esquema):
    activas: bool = Field(
        ..., description="perfil_usuario.perf_notificaciones_activas (interruptor general)."
    )
    categorias: dict[CategoriaNotificacion, bool]
