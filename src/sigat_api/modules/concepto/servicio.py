"""Casos de uso de concepto y resúmenes. ``ServicioConcepto.reemitir`` implementa
``sincronizacion.puertos.PuertoConcepto``."""

from datetime import date

from sigat_api.compartido.errores import NoImplementado
from sigat_api.compartido.tipos import Actor
from sigat_api.modules.concepto import esquemas as e
from sigat_api.modules.concepto.repositorio import RepositorioConcepto


class ServicioConcepto:
    def __init__(self, repo: RepositorioConcepto) -> None:
        self._repo = repo

    async def reemitir(self, peri_id: int, indi_id: int, motivo: str) -> None:
        """Emite versión n+1 del concepto del periodo: ``apto`` (por_debajo_umbral), ``no_apto``
        (igual_o_superior_umbral) o ``no_emitido`` (sin_umbral). ``conc_fecha_efecto`` = fecha de
        observación del registro que lo disparó. Si el resultado no cambia, no crea versión."""
        raise NoImplementado("Reemisión del concepto")

    async def resumen_lote(self, actor: Actor, lote_id: int) -> e.ResumenLote:
        raise NoImplementado("Resumen del lote")

    async def serie_mtd(
        self, actor: Actor, lote_id: int, desde: date | None, hasta: date | None
    ) -> list[e.PuntoMtd]:
        raise NoImplementado("Serie del MTD")

    async def periodos(self, actor: Actor, lote_id: int) -> list[e.PeriodoTrampeo]:
        raise NoImplementado("Periodos")

    async def versiones_mtd(self, actor: Actor, lote_id: int, peri_id: int) -> list[e.VersionMtd]:
        raise NoImplementado("Versiones del MTD")

    async def conceptos(self, actor: Actor, lote_id: int) -> list[e.Concepto]:
        raise NoImplementado("Conceptos del lote")

    async def concepto_a_fecha(self, actor: Actor, lote_id: int, fecha: date) -> e.ConceptoAFecha:
        raise NoImplementado("Concepto a una fecha")

    async def etapa(self, actor: Actor, lote_id: int, fecha: date | None) -> e.EtapaLote:
        raise NoImplementado("Etapa fenológica")

    async def cultivo_productor(self, actor: Actor) -> e.CultivoProductor:
        """Solo PRODUCTOR: sus lotes (predios de los que es dueño)."""
        raise NoImplementado("Cultivo del productor")
