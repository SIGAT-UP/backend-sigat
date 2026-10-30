"""Casos de uso de auditoría."""

from datetime import datetime

from sigat_api.compartido.errores import NoImplementado
from sigat_api.compartido.esquemas import Pagina
from sigat_api.compartido.tipos import Actor
from sigat_api.modules.auditoria import esquemas as e
from sigat_api.modules.auditoria.repositorio import RepositorioAuditoria

# bita_tabla -> categoría que muestra la web
CATEGORIAS: dict[str, e.CategoriaAuditoria] = {
    "usuario": "Usuarios",
    "persona": "Usuarios",
    "usuario_predio": "Usuarios",
    "predio": "Predio",
    "lote": "Predio",
    "lote_geometria": "Predio",
    "reticula": "Predio",
    "trampa": "Trampas",
    "ubicacion_trampa": "Trampas",
    "programa_inspeccion": "Configuración",
    "paquete_campo": "Configuración",
    "lectura_trampa": "Registros",
    "visita": "Registros",
    "aplicacion_fitosanitaria": "Registros",
    "cosecha": "Registros",
    "planificacion": "Registros",
    "concepto_aptitud": "Registros",
}


class ServicioAuditoria:
    def __init__(self, repo: RepositorioAuditoria) -> None:
        self._repo = repo

    async def listar(
        self,
        actor: Actor,
        desde: datetime | None,
        hasta: datetime | None,
        categoria: e.CategoriaAuditoria | None,
        usua_id: int | None,
        con_detalle: bool,
        cursor: str | None,
    ) -> Pagina[e.EntradaAuditoria]:
        """Solo ADMINISTRADOR. Ver el detalle de una fila con datos personales registra ACCESO."""
        raise NoImplementado("Bitácora")

    async def recientes(self, actor: Actor, limite: int) -> list[e.EntradaAuditoria]:
        raise NoImplementado("Actividad reciente del sistema")
