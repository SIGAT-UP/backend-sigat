"""Lo que IDENTIDAD necesita de otros módulos. Se inyecta en ``api/fabricas.py``."""

from typing import Protocol
from uuid import UUID


class PuertoDispositivos(Protocol):
    """Lo implementa el módulo de sincronización (tabla ``dispositivo``)."""

    async def registrar_o_actualizar(
        self, disp_id: UUID | None, plataforma: str, version_app: str | None, nombre: str | None, usua_id: int
    ) -> UUID:
        """Devuelve el ``disp_id``. Rechaza un ``disp_id`` dado de baja (``disp_activo = false``)."""
        ...


class PuertoArchivos(Protocol):
    """Lo implementa el módulo de imágenes."""

    async def exigir_almacenado(self, arch_id: UUID, clase: str, usua_id: int) -> None:
        """Falla si el archivo no existe, no es de esa clase, no es del usuario o no está ``almacenado``."""
        ...

    async def url_temporal(self, arch_id: UUID) -> str: ...


class PuertoAvisos(Protocol):
    """Lo implementa el módulo de notificaciones (tabla ``notificacion``)."""

    async def emitir(
        self,
        usua_id: int,
        categoria: str,
        titulo: str,
        cuerpo: str,
        evento_clave: str,
        ruta: str | None = None,
        argumento: str | None = None,
    ) -> bool:
        """Crea el aviso (idempotente por ``evento_clave``). True si lo creó."""
        ...
