"""Casos de uso de concepto y resúmenes. ``ServicioConcepto.reemitir`` implementa
``sincronizacion.puertos.PuertoConcepto``."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sigat_api.compartido.errores import NoEncontrado, NoImplementado, ReglaNegocio
from sigat_api.compartido.tipos import Actor, ResultadoConcepto, ResultadoContraste
from sigat_api.modules.concepto import esquemas as e
from sigat_api.modules.concepto.repositorio import RepositorioConcepto

ZONA_PREDETERMINADA = "America/Bogota"

_EXPLICACION = {
    ResultadoConcepto.APTO: "Apto: el MTD del periodo estaba por debajo del umbral.",
    ResultadoConcepto.NO_APTO: "No apto: el MTD del periodo igualaba o superaba el umbral.",
    ResultadoConcepto.NO_EMITIDO: "No emitido: no había umbral configurado para esa fecha.",
}
SIN_CONCEPTO = "Sin concepto: a esa fecha aún no se había emitido ningún concepto para el lote."

_MAPA_CONCEPTO: dict[str, ResultadoConcepto] = {
    ResultadoContraste.POR_DEBAJO_UMBRAL.value: ResultadoConcepto.APTO,
    ResultadoContraste.IGUAL_O_SUPERIOR_UMBRAL.value: ResultadoConcepto.NO_APTO,
    ResultadoContraste.SIN_UMBRAL.value: ResultadoConcepto.NO_EMITIDO,
}


def derivar_resultado_concepto(contraste: ResultadoContraste | str | None) -> ResultadoConcepto:
    """Deriva el concepto de aptitud a partir del contraste del MTD (RF-024 / fn_concepto_valida)."""
    if contraste is None:
        return ResultadoConcepto.NO_EMITIDO
    clave = contraste.value if isinstance(contraste, ResultadoContraste) else str(contraste)
    return _MAPA_CONCEPTO.get(clave, ResultadoConcepto.NO_EMITIDO)


def explicar_concepto(concepto: e.Concepto | None) -> str:
    """Texto de RF-024 para quien consulta: emitido (apto / no apto), no emitido (sin umbral) o
    ausencia de concepto. Distingue "no había umbral" de "no se había emitido nada"."""
    if concepto is None:
        return SIN_CONCEPTO
    return _EXPLICACION[ResultadoConcepto(concepto.conc_resultado)]


def etapa_lote(fila: dict[str, Any]) -> e.EtapaLote:
    """RN-012: la etapa se DERIVA; la declarada convive. Solo hay discrepancia si existen ambas y
    difieren (sin regla o sin declaración no se afirma nada)."""
    derivada, declarada = fila.get("derivada"), fila.get("declarada")
    return e.EtapaLote(
        derivada=derivada,
        declarada=declarada,
        declarada_el=fila.get("declarada_el"),
        discrepancia=derivada is not None and declarada is not None and derivada != declarada,
    )


def periodo_actual(periodos: list[e.PeriodoTrampeo]) -> e.PeriodoTrampeo | None:
    """El periodo abierto más reciente; si no hay abierto, ninguno (no se inventa uno)."""
    abiertos = [p for p in periodos if p.peri_estado == "abierto"]
    return max(abiertos, key=lambda p: (p.peri_inicio, p.peri_id)) if abiertos else None


def revision_pendiente(visitas_por_revisar: int) -> str | None:
    if visitas_por_revisar <= 0:
        return None
    if visitas_por_revisar == 1:
        return "1 visita por revisar"
    return f"{visitas_por_revisar} visitas por revisar"


@dataclass(frozen=True, slots=True)
class DatosCultivo:
    """Todo ``CultivoProductor`` salvo ``lotes_revisados`` (sin definición) y ``ultimo_mtd`` (sin
    criterio para elegir un MTD entre varios lotes): ambos pendientes del Owner."""

    cultivo: str | None
    vigilancia_activa: bool
    ultima_visita: datetime | None
    ultima_aplicacion: datetime | None
    lotes: list[e.LoteCultivo]


@dataclass(frozen=True, slots=True)
class InicioProductorDatos:
    lotes: int
    planificaciones_por_responder: int
    ultima_visita: datetime | None


def rango_trampas(trampas: int, primera: str | None, ultima: str | None) -> str | None:
    """Informe de consumo §5.2 («Trampas del ICA: ICA-001 a ICA-004», origen
    ``v_trampa_lote_vigente.tram_codigo``): códigos de la primera y la última trampa ubicadas hoy en
    el lote, por número. Una sola trampa: su código. Ninguna: ``None``."""
    if trampas <= 0 or primera is None:
        return None
    if trampas == 1 or ultima is None or ultima == primera:
        return primera
    return f"{primera} a {ultima}"


def _mas_reciente(valores: list[datetime | None]) -> datetime | None:
    presentes = [v for v in valores if v is not None]
    return max(presentes) if presentes else None


def datos_cultivo(filas: list[dict[str, Any]]) -> DatosCultivo:
    """Arma el cultivo del productor a partir de las filas de ``RepositorioConcepto.cultivo_lotes``.

    * ``cultivo``: la especie (``v_lote_app.cultivo``) cuando todos los lotes que la tienen comparten
      una sola; si hay varias o ninguna, ``None`` (no se elige una).
    * ``vigilancia_activa``: ``True`` si ALGÚN lote tiene periodo de trampeo abierto (definición por lote
      de ``v_lote_app``). La agregación «alguno» es una interpretación PROVISIONAL, pendiente de
      confirmación del Owner.
    * ``ultima_visita`` / ``ultima_aplicacion``: la más reciente entre los lotes (PW01: ``max``)."""
    lotes = [
        e.LoteCultivo(
            lote_id=f["lote_id"],
            lote_descripcion=f["lote_descripcion"],
            mtd=f["mtd"],
            rango_trampas=rango_trampas(int(f["trampas"] or 0), f["primera_trampa"], f["ultima_trampa"]),
            ultima_visita=f["ultima_visita"],
            ultima_aplicacion=f["ultima_aplicacion"],
            cosecha_esperada=f["cosecha_esperada"],
            volumen_esperado=f["volumen_esperado"],
            concepto=f["concepto"],
        )
        for f in filas
    ]
    especies = {f["cultivo"] for f in filas if f["cultivo"] is not None}
    return DatosCultivo(
        cultivo=especies.pop() if len(especies) == 1 else None,
        vigilancia_activa=any(bool(f["vigilancia_activa"]) for f in filas),
        ultima_visita=_mas_reciente([lote.ultima_visita for lote in lotes]),
        ultima_aplicacion=_mas_reciente([lote.ultima_aplicacion for lote in lotes]),
        lotes=lotes,
    )


def armar_cultivo(datos: DatosCultivo, lotes_revisados: int) -> e.CultivoProductor:
    """``CultivoProductor`` completo. ``ultimo_mtd`` va en ``None``: el MTD de cada lote viaja en
    ``lotes[].mtd`` y no hay criterio aprobado para elegir uno solo."""
    return e.CultivoProductor(
        cultivo=datos.cultivo,
        vigilancia_activa=datos.vigilancia_activa,
        lotes_revisados=lotes_revisados,
        ultima_visita=datos.ultima_visita,
        ultimo_mtd=None,
        ultima_aplicacion=datos.ultima_aplicacion,
        lotes=datos.lotes,
    )


class ServicioConcepto:
    def __init__(self, repo: RepositorioConcepto, zona_horaria: str = ZONA_PREDETERMINADA) -> None:
        self._repo = repo
        self._zona = zona_horaria

    async def reemitir(self, peri_id: int, indi_id: int, motivo: str) -> None:
        """Emite versión n+1 del concepto del periodo: ``apto`` (por_debajo_umbral), ``no_apto``
        (igual_o_superior_umbral) o ``no_emitido`` (sin_umbral). ``conc_fecha_efecto`` = fecha de
        observación del registro que lo disparó. Si el resultado no cambia, no crea versión."""
        datos = await self._repo.datos_reemision(peri_id, indi_id)
        if datos is None:
            raise NoEncontrado("El periodo o índice MTD no existe.", codigo="PERIODO_NO_ENCONTRADO")

        resultado = derivar_resultado_concepto(datos.get("contraste"))
        vigente = datos.get("resultado_vigente")
        if vigente is not None and str(vigente) == resultado.value:
            return

        fecha_efecto = datos.get("fecha_efecto")
        if isinstance(fecha_efecto, datetime):
            fecha_efecto = fecha_efecto.date()
        elif not isinstance(fecha_efecto, date):
            fecha_efecto = datos["peri_fin"]

        await self._repo.insertar_concepto(
            {
                "lote_id": datos["lote_id"],
                "peri_id": peri_id,
                "indi_id": indi_id,
                "conc_resultado": resultado.value,
                "conc_fecha_efecto": fecha_efecto,
                "norm_id": datos.get("norm_id"),
                "conc_motivo": motivo,
            }
        )

    async def _exigir_lote_visible(self, actor: Actor, lote_id: int) -> None:
        if not await self._repo.lote_visible(actor.usua_id, lote_id):
            raise NoEncontrado("El lote no existe o no es visible para usted.", codigo="LOTE_NO_ENCONTRADO")

    async def resumen_lote(self, actor: Actor, lote_id: int) -> e.ResumenLote:
        await self._exigir_lote_visible(actor, lote_id)
        fila = await self._repo.resumen(actor.usua_id, lote_id, self._zona)

        if fila is None:  # el lote no existe o no es visible
            raise NoEncontrado("El lote no existe o no es visible para usted.", codigo="LOTE_NO_ENCONTRADO")

        periodos = [e.PeriodoTrampeo(**p) for p in await self._repo.periodos(lote_id)]
        serie = [e.PuntoMtd(**p) for p in await self._repo.serie(actor.usua_id, lote_id, None, None)]
        etapa_dict = await self._repo.etapa(lote_id, None, self._zona)
        etapa = etapa_lote(etapa_dict)
        # Excluir los campos que el servicio construye explícitamente para evitar colisión de kwargs.
        _construidos = {"mtd_es_estimacion", "periodo_actual", "etapa", "revision_pendiente", "serie"}
        datos = {k: v for k, v in fila.items() if k in e.ResumenLote.model_fields and k not in _construidos}
        return e.ResumenLote(
            **datos,
            mtd_es_estimacion=False,  # ADR-15: la cifra del servidor es la autorizada
            periodo_actual=periodo_actual(periodos),
            etapa=etapa,
            revision_pendiente=revision_pendiente(int(fila.get("visitas_por_revisar") or 0)),
            serie=serie,
        )

    async def serie_mtd(
        self, actor: Actor, lote_id: int, desde: date | None, hasta: date | None
    ) -> list[e.PuntoMtd]:
        if desde is not None and hasta is not None and desde > hasta:
            raise ReglaNegocio(
                "La fecha inicial no puede ser posterior a la final.", codigo="RANGO_FECHAS_INVALIDO"
            )
        await self._exigir_lote_visible(actor, lote_id)
        filas = await self._repo.serie(actor.usua_id, lote_id, desde, hasta)
        return [e.PuntoMtd(**f) for f in filas]

    async def periodos(self, actor: Actor, lote_id: int) -> list[e.PeriodoTrampeo]:
        await self._exigir_lote_visible(actor, lote_id)
        return [e.PeriodoTrampeo(**f) for f in await self._repo.periodos(lote_id)]

    async def versiones_mtd(self, actor: Actor, lote_id: int, peri_id: int) -> list[e.VersionMtd]:
        await self._exigir_lote_visible(actor, lote_id)
        if not await self._repo.periodo_de_lote(lote_id, peri_id):
            raise NoEncontrado("El periodo no existe en este lote.", codigo="PERIODO_NO_ENCONTRADO")
        return [e.VersionMtd(**f) for f in await self._repo.versiones_mtd(peri_id)]

    async def conceptos(self, actor: Actor, lote_id: int) -> list[e.Concepto]:
        await self._exigir_lote_visible(actor, lote_id)
        return [e.Concepto(**f) for f in await self._repo.conceptos(lote_id)]

    async def concepto_a_fecha(self, actor: Actor, lote_id: int, fecha: date) -> e.ConceptoAFecha:
        """RF-024: el estado que se habría obtenido ESE día, no el de hoy."""
        await self._exigir_lote_visible(actor, lote_id)
        fila = await self._repo.concepto_a_fecha(lote_id, fecha, self._zona)
        concepto = e.Concepto(**fila) if fila is not None else None
        return e.ConceptoAFecha(
            fecha_consulta=fecha, concepto=concepto, explicacion=explicar_concepto(concepto)
        )

    async def etapa(self, actor: Actor, lote_id: int, fecha: date | None) -> e.EtapaLote:
        await self._exigir_lote_visible(actor, lote_id)
        return etapa_lote(await self._repo.etapa(lote_id, fecha, self._zona))

    async def datos_cultivo(self, actor: Actor) -> DatosCultivo:
        """Lotes activos y visibles del actor (``fn_lotes_visibles``) con sus indicadores (PW01/PW02).
        Nunca incluye lotes ajenos; sin lotes devuelve una lista vacía."""
        return datos_cultivo(await self._repo.cultivo_lotes(actor.usua_id))

    async def cultivo_productor(self, actor: Actor) -> e.CultivoProductor:
        """GET /productor/cultivo. Sigue respondiendo 501: ``lotes_revisados`` es obligatorio en el
        contrato y no tiene definición (informe de consumo §9.1.3 y §9.4: el rótulo es erróneo, el
        valor sería ``count(lectura_trampa)`` y no se define su alcance). Pendiente del Owner.
        Cuando se defina: ``armar_cultivo(await self.datos_cultivo(actor), lotes_revisados)``."""
        raise NoImplementado(
            "Cultivo del productor: falta la definición oficial de lotes_revisados (pendiente del Owner)"
        )

    async def inicio_productor(self, actor: Actor) -> InicioProductorDatos:
        """Bloque ``productor`` de GET /yo/inicio (PW01). ``ultimo_mtd`` no se incluye: no hay un
        criterio aprobado para elegir un MTD entre varios lotes (pendiente del Owner)."""
        datos = await self.datos_cultivo(actor)
        return InicioProductorDatos(
            lotes=len(datos.lotes),
            planificaciones_por_responder=await self._repo.planificaciones_por_responder(actor.usua_id),
            ultima_visita=datos.ultima_visita,
        )
