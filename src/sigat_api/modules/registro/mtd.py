"""MOTOR DE UMBRALES MTD (Arquitectura §5.4, ADR-13, RN-001).

El MTD con AUTORIDAD se calcula SOLO aquí. El dispositivo muestra una
estimación marcada como tal (ADR-15) y nunca la envía como dato.

    MTD = M / (T × D)        [moscas / trampa / día]
    M = moscas capturadas en las trampas atendidas del periodo (lecturas vigentes,
        linaje inspeccion_oficial, no anuladas, lect_leida = true)
    T = trampas atendidas
    D = promedio de días de exposición
    T × D = 0  -> indi_valor NULL

Contraste (RF-024) con el umbral de ``programa_inspeccion`` VIGENTE EN LA FECHA DEL
PERIODO (no el de hoy). Sin umbral -> ``sin_umbral`` y el concepto queda ``no_emitido``
(UQQ-004: el umbral oficial no existe todavía; NO se inventa).
"""

from dataclasses import dataclass
from decimal import Decimal

from sigat_api.compartido.errores import NoImplementado
from sigat_api.compartido.tipos import ResultadoContraste


@dataclass(frozen=True, slots=True)
class EntradaMtd:
    moscas: int
    trampas: int
    dias_exposicion: Decimal
    umbral: Decimal | None


@dataclass(frozen=True, slots=True)
class SalidaMtd:
    valor: Decimal | None
    contraste: ResultadoContraste


def calcular(entrada: EntradaMtd) -> SalidaMtd:
    """Función pura. Definir con el equipo: redondeo (indi_valor es numeric(14,6)) y si
    'igual' al umbral cuenta como superior (el dominio dice ``igual_o_superior_umbral``)."""
    raise NoImplementado("Cálculo del MTD")


class MotorMtd:
    """Orquesta el recálculo de un periodo: lee lecturas vigentes, inserta ``indice_mtd``
    versión n+1 con ``indi_motivo_recalculo`` y ``indice_mtd_lectura``. Append-only."""

    async def recalcular_periodo(self, peri_id: int, motivo: str) -> int:
        """Devuelve el nuevo ``indi_id``. Idempotente: si el resultado no cambia, no crea versión."""
        raise NoImplementado("Recálculo del MTD del periodo")
