"""Cola de trabajo interna (contenedor 10 del C4): reproceso asíncrono.

Se implementa con ``procrastinate`` sobre la MISMA PostgreSQL, en el esquema
``cola`` (ADR-14: es una cola del mismo despliegue, no un servicio aparte).
El proceso ``python -m sigat_api.worker`` consume las tareas.

Tareas definidas (nombres estables; el payload es mínimo y re-ejecutable):
* ``reprocesar_periodo``   {peri_id, motivo, oper_id}   -> recalcula MTD y reemite concepto
* ``generar_paquete_campo`` {pred_id, motivo}           -> nueva versión del paquete de campo
* ``verificar_archivo``    {arch_id}                    -> recalcula SHA-256 y marca almacenado/rechazado
* ``enviar_correo``        {plantilla, usua_id, datos}  -> recuperación de contraseña

Todas deben ser IDEMPOTENTES: la cola puede ejecutar dos veces la misma tarea.
"""

from typing import Any, Protocol

TAREA_REPROCESAR_PERIODO = "reprocesar_periodo"
TAREA_GENERAR_PAQUETE = "generar_paquete_campo"
TAREA_VERIFICAR_ARCHIVO = "verificar_archivo"
TAREA_ENVIAR_CORREO = "enviar_correo"


class Cola(Protocol):
    async def encolar(self, tarea: str, datos: dict[str, Any], *, clave_unica: str | None = None) -> None:
        """``clave_unica`` evita encolar dos veces el mismo reproceso pendiente (queueing_lock)."""
        ...


class ColaProcrastinate:
    """Adaptador sobre ``procrastinate.App`` con ``PsycopgConnector``/``AsyncpgConnector``."""

    async def encolar(self, tarea: str, datos: dict[str, Any], *, clave_unica: str | None = None) -> None:
        from sigat_api.compartido.errores import NoImplementado

        raise NoImplementado(f"Encolar tarea {tarea}")
