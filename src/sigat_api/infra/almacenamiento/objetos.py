"""Almacén de objetos S3 compatible (Arquitectura §3.6: los binarios no van a la BD).

La BD guarda solo ``archivo_adjunto.arch_ref_almacenamiento`` (clave del objeto).
Clave sugerida: ``{clase}/{aaaa}/{mm}/{arch_id}`` — sin nombres de personas.
"""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sigat_api.compartido.errores import NoImplementado
from sigat_api.config import Configuracion


@dataclass(frozen=True, slots=True)
class UrlFirmada:
    metodo: str
    url: str
    cabeceras: dict[str, str]
    expira_en_segundos: int


class AlmacenObjetos(Protocol):
    async def url_subida(self, clave: str, mime: str, tamano: int, sha256_hex: str) -> UrlFirmada: ...
    async def url_descarga(self, clave: str, nombre_descarga: str | None) -> UrlFirmada: ...
    async def leer_sha256(self, clave: str) -> str: ...
    async def guardar(self, clave: str, contenido: bytes, mime: str) -> None: ...


class AlmacenS3:
    """Implementación con aioboto3. Exigir ``x-amz-checksum-sha256`` en la subida firmada."""

    def __init__(self, cfg: Configuracion) -> None:
        self._cfg = cfg

    async def url_subida(self, clave: str, mime: str, tamano: int, sha256_hex: str) -> UrlFirmada:
        raise NoImplementado("URL firmada de subida")

    async def url_descarga(self, clave: str, nombre_descarga: str | None) -> UrlFirmada:
        raise NoImplementado("URL firmada de descarga")

    async def leer_sha256(self, clave: str) -> str:
        raise NoImplementado("Verificación de huella del objeto")

    async def guardar(self, clave: str, contenido: bytes, mime: str) -> None:
        raise NoImplementado("Subida directa por la API")


def clave_objeto(clase: str, arch_id: UUID, anio: int, mes: int) -> str:
    return f"{clase}/{anio:04d}/{mes:02d}/{arch_id}"
