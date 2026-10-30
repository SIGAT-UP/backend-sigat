"""Casos de uso de archivos. Implementa ``identidad.puertos.PuertoArchivos``."""

from uuid import UUID

from sigat_api.compartido.errores import NoImplementado
from sigat_api.compartido.tipos import Actor
from sigat_api.infra.almacenamiento.objetos import AlmacenObjetos, UrlFirmada
from sigat_api.infra.cola.cola import Cola
from sigat_api.modules.imagenes import esquemas as e
from sigat_api.modules.imagenes.repositorio import RepositorioArchivos


class ServicioArchivos:
    def __init__(self, repo: RepositorioArchivos, almacen: AlmacenObjetos, cola: Cola) -> None:
        self._repo = repo
        self._almacen = almacen
        self._cola = cola

    async def declarar(self, actor: Actor, s: e.NuevoArchivo) -> e.RespuestaNuevoArchivo:
        """Paso 1. Idempotente por ``arch_id``: si existe con el mismo hash devuelve el mismo
        archivo (y una URL nueva si sigue pendiente); con hash distinto -> 409.
        Límites de tamaño y MIME por clase. Devuelve URL firmada PUT con checksum SHA-256."""
        raise NoImplementado("Declarar archivo")

    async def subir_contenido(self, actor: Actor, arch_id: UUID, contenido: bytes, mime: str) -> e.Archivo:
        """Paso 2 alternativo (sin URL firmada): la API recibe el binario. Verifica SHA-256 y
        el tipo por la firma de bytes (no por la extensión); limpia metadatos EXIF de ubicación
        si la política lo exige (SEGURIDAD S-13 del móvil). Marca almacenado o rechazado."""
        raise NoImplementado("Subir contenido")

    async def confirmar_subida(self, actor: Actor, arch_id: UUID) -> e.Archivo:
        """Tras el PUT directo al almacén: encola ``verificar_archivo``."""
        raise NoImplementado("Confirmar subida")

    async def obtener(self, actor: Actor, arch_id: UUID) -> e.Archivo:
        """Visible si: es del actor, o está ligado a un registro/planificación que el actor puede ver."""
        raise NoImplementado("Archivo")

    async def enlace_descarga(self, actor: Actor, arch_id: UUID) -> UrlFirmada:
        """URL firmada corta. Registrar ACCESO en bitácora si es foto con personas (ADR-11)."""
        raise NoImplementado("Descarga")

    async def vincular_evidencia(self, actor: Actor, s: e.VinculoEvidencia) -> e.Evidencia:
        """Liga una foto ``almacenada`` (clase foto_evidencia) a UNA lectura, hallazgo, visita o
        actividad planificada (excluyentes, CHECK de la BD). Idempotente por ``evid_id``.
        Crea la operación ``evidencia``/``crear`` con registro = evid_id (BD v9, disparador
        fn_evidencia_operacion_valida) y luego la fila de evidencia, en la misma transacción.
        Varias fotos por lectura: cada una con su operación."""
        raise NoImplementado("Vincular evidencia")

    # --- puerto para identidad / planificación
    async def exigir_almacenado(self, arch_id: UUID, clase: str, usua_id: int) -> None:
        raise NoImplementado("Validar archivo almacenado")

    async def url_temporal(self, arch_id: UUID) -> str:
        raise NoImplementado("URL temporal")
