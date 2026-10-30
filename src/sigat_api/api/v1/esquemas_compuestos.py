"""Respuestas que componen datos de VARIOS módulos (solo la capa API puede hacerlo)."""

from datetime import date, datetime
from typing import Literal

from pydantic import Field

from sigat_api.compartido.esquemas import Esquema
from sigat_api.compartido.tipos import RolCodigo
from sigat_api.modules.auditoria.esquemas import EntradaAuditoria


class Salud(Esquema):
    estado: Literal["ok"]


class Listo(Esquema):
    estado: Literal["ok", "degradado"]
    base_datos: bool
    almacen_objetos: bool
    cola: bool


class HoraServidor(Esquema):
    """R-T6: el móvil compara su reloj con este valor al iniciar la visita."""

    servidor_utc: datetime
    zona_horaria_predeterminada: str


class VersionServicio(Esquema):
    api: str
    contrato: str = Field(..., description="Hash corto de contracts/openapi.json.")
    version_minima_app: str | None


class InicioTecnico(Esquema):
    lotes_asignados: int
    actividades_pendientes: int
    proxima_actividad: datetime | None
    ultima_sincronizacion: datetime | None
    operaciones_por_decidir: int


class InicioProductor(Esquema):
    lotes: int
    planificaciones_por_responder: int
    ultimo_mtd: float | None
    ultima_visita: datetime | None


class InicioAgronomo(Esquema):
    registros_por_revisar: int
    planificaciones_pendientes: int
    actividades_en_curso: int
    lotes_sobre_umbral: int


class InicioResumen(Esquema):
    """Pantalla de inicio de cada rol. Solo viene lleno el bloque del rol del actor."""

    rol: RolCodigo
    fecha: date
    datos_al: datetime = Field(..., description="Web 'Datos al 08 oct · 14:20'.")
    notificaciones_no_leidas: int
    tecnico: InicioTecnico | None = None
    productor: InicioProductor | None = None
    agronomo: InicioAgronomo | None = None


class IndicadorSistema(Esquema):
    etiqueta: str
    valor: str
    tono: Literal["ok", "warn"]


class PendienteSistema(Esquema):
    titulo: str
    nota: str
    destacado: bool = False


class ResumenAdministracion(Esquema):
    """Web ``AdminOverview``."""

    usuarios_activos: int
    roles: int
    trampas: int
    predios: int
    sistema: list[IndicadorSistema]
    recientes: list[EntradaAuditoria]
    pendientes: list[PendienteSistema]
