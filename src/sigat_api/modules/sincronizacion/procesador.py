"""PROCESADOR DE REPROCESO (Arquitectura §6.3). Lo ejecuta el worker, no la petición HTTP.

Tarea ``reprocesar_periodo`` {peri_id, motivo, oper_id}:
1. ``PuertoRecalculo.recalcular_periodo`` -> nueva versión de indice_mtd (si cambió).
2. ``PuertoConcepto.reemitir`` -> nueva versión de concepto_aptitud con
   ``conc_fecha_efecto`` = t_observacion del registro que lo disparó (Arquitectura §4.4).
3. Notificar a agrónomo/productor si el concepto cambió (categoría alertas_fitosanitarias).
Debe ser idempotente: ejecutar dos veces la misma tarea no crea versiones duplicadas.
"""

from sigat_api.compartido.errores import NoImplementado
from sigat_api.modules.sincronizacion.puertos import PuertoConcepto, PuertoRecalculo


class ProcesadorReproceso:
    def __init__(self, recalculo: PuertoRecalculo, concepto: PuertoConcepto) -> None:
        self._recalculo = recalculo
        self._concepto = concepto

    async def ejecutar(self, peri_id: int, motivo: str, oper_id: int | None) -> None:
        raise NoImplementado("Reproceso del periodo")
