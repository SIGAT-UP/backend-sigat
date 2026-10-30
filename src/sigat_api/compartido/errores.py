"""Errores de dominio comunes a todos los módulos.

Los módulos lanzan estas excepciones; la capa HTTP (``api/errores.py``) las
traduce a ``application/problem+json`` (RFC 9457). Un módulo nunca construye
respuestas HTTP.
"""


class ErrorDominio(Exception):
    """Base. ``codigo`` es estable y lo usan los fronts para decidir qué mostrar."""

    estado_http: int = 400
    codigo: str = "ERROR_DOMINIO"
    titulo: str = "No se pudo completar la operación"

    def __init__(
        self, detalle: str, *, codigo: str | None = None, errores: list[dict[str, str]] | None = None
    ):
        super().__init__(detalle)
        self.detalle = detalle
        if codigo:
            self.codigo = codigo
        self.errores = errores or []


class NoAutenticado(ErrorDominio):
    estado_http = 401
    codigo = "NO_AUTENTICADO"
    titulo = "Sesión no válida"


class Prohibido(ErrorDominio):
    estado_http = 403
    codigo = "PROHIBIDO"
    titulo = "No tiene permiso para esta acción"


class NoEncontrado(ErrorDominio):
    estado_http = 404
    codigo = "NO_ENCONTRADO"
    titulo = "No existe o no es visible para usted"


class Conflicto(ErrorDominio):
    """El estado actual impide la operación (ya respondida, duplicado, solapamiento)."""

    estado_http = 409
    codigo = "CONFLICTO"
    titulo = "La operación entra en conflicto con el estado actual"


class ReglaNegocio(ErrorDominio):
    """Los datos tienen forma válida pero incumplen una regla (RN-xxx, Arquitectura §5.3)."""

    estado_http = 422
    codigo = "REGLA_NEGOCIO"
    titulo = "Los datos no cumplen una regla del programa"


class PreCondicionFallida(ErrorDominio):
    """If-Match / versión esperada no coincide (concurrencia optimista)."""

    estado_http = 412
    codigo = "PRECONDICION_FALLIDA"
    titulo = "El recurso cambió desde que lo consultó"


class DemasiadasSolicitudes(ErrorDominio):
    estado_http = 429
    codigo = "DEMASIADAS_SOLICITUDES"
    titulo = "Demasiados intentos"


class NoImplementado(ErrorDominio):
    """Marcador del esqueleto: el endpoint existe en el contrato pero falta programarlo.

    Se lanza con el nombre de la funcionalidad (``NoImplementado("Listado de lotes")``) y el
    ``detail`` que ven las pantallas queda: "Listado de lotes: pendiente de implementar en el backend."
    """

    estado_http = 501
    codigo = "NO_IMPLEMENTADO"
    titulo = "Funcionalidad pendiente de implementar"

    def __init__(self, funcionalidad: str, **kwargs: object) -> None:
        super().__init__(f"{funcionalidad}: pendiente de implementar en el backend.", **kwargs)  # type: ignore[arg-type]
