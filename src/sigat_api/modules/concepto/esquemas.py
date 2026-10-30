"""Contrato HTTP de concepto, MTD y resúmenes."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import Field

from sigat_api.compartido.esquemas import Esquema
from sigat_api.compartido.tipos import ResultadoConcepto, ResultadoContraste


class PeriodoTrampeo(Esquema):
    peri_id: int
    lote_id: int
    vigi_id: int
    prog_id: int
    peri_inicio: date
    peri_fin: date
    peri_estado: str


class PuntoMtd(Esquema):
    """Fila de ``v_mtd_serie_lote`` (móvil ``MtdPoint``, web ``MtdPoint``)."""

    peri_id: int
    peri_inicio: date
    peri_fin: date
    mtd: Decimal | None
    moscas: int
    trampas: int
    dias_exposicion: Decimal
    umbral: Decimal | None
    contraste: ResultadoContraste
    escenario: str | None


class VersionMtd(Esquema):
    """Historia de recálculos de un periodo: 'MTD 2,1 %, recalculado el día 24 a 1,4 %' (§4.4)."""

    indi_id: int
    indi_version: int
    indi_valor: Decimal | None
    indi_moscas: int
    indi_trampas: int
    indi_dias_exposicion: Decimal
    indi_umbral_aplicado: Decimal | None
    indi_resultado_contraste: ResultadoContraste
    escenario: str | None
    indi_calculado_en: datetime
    indi_motivo_recalculo: str | None


class Concepto(Esquema):
    conc_id: int
    lote_id: int
    peri_id: int
    conc_version: int
    conc_resultado: ResultadoConcepto
    conc_fecha_efecto: date
    norma: str | None
    conc_emitido_en: datetime
    conc_motivo: str | None
    mtd: Decimal | None


class ConceptoAFecha(Esquema):
    """RF-024: el estado que se habría obtenido ESE día, no el de hoy."""

    fecha_consulta: date
    concepto: Concepto | None
    explicacion: str = Field(
        ..., description="Ej.: 'No emitido: no había umbral configurado para esa fecha'."
    )


class EtapaLote(Esquema):
    """RN-012: la etapa se DERIVA; la declarada convive y se marca la discrepancia."""

    derivada: str | None = Field(None, description="fn_etapa_derivada(lote, fecha).")
    declarada: str | None
    declarada_el: datetime | None
    discrepancia: bool


class ResumenLote(Esquema):
    """``v_lote_resumen_app`` + serie. Alimenta: móvil LotSummary, web LotControl/Summary,
    productor LotStatusSummary."""

    lote_id: int
    lote_descripcion: str
    mtd: Decimal | None
    mtd_es_estimacion: bool = Field(False, description="Siempre false en el servidor (ADR-15).")
    periodo_actual: PeriodoTrampeo | None
    escenario: str | None
    umbral: Decimal | None = Field(..., description="Nulo = 'Sin definir' (UQQ-004).")
    contraste: ResultadoContraste | None
    concepto: ResultadoConcepto | None
    concepto_fecha_efecto: date | None
    inspecciones: int
    inspecciones_mes: int
    aplicaciones: int
    ultima_aplicacion: datetime | None
    lecturas: int
    especimenes: int
    trampas_vigentes: int
    trampas_con_capturas: int
    ultima_visita: datetime | None
    etapa: EtapaLote
    ultima_cosecha: date | None
    cosecha_esperada: date | None
    rendimiento_estimado: Decimal | None
    rendimiento_real: Decimal | None
    hallazgos: int
    revision_pendiente: str | None
    serie: list[PuntoMtd]


class LoteCultivo(Esquema):
    lote_id: int
    lote_descripcion: str
    mtd: Decimal | None
    rango_trampas: str | None
    ultima_visita: datetime | None
    ultima_aplicacion: datetime | None
    cosecha_esperada: date | None
    volumen_esperado: Decimal | None
    concepto: ResultadoConcepto | None


class CultivoProductor(Esquema):
    """Web ``cropLots`` / móvil ``CropSummary``."""

    cultivo: str | None
    vigilancia_activa: bool
    lotes_revisados: int
    ultima_visita: datetime | None
    ultimo_mtd: Decimal | None
    ultima_aplicacion: datetime | None
    lotes: list[LoteCultivo]
