"""PW01/PW02 — cultivo del productor y bloque ``productor`` del inicio. Sin base de datos.

``GET /productor/cultivo`` sigue en 501 hasta que el Owner defina ``lotes_revisados``; aquí se prueban
las piezas ya implementadas: el armado de los datos, el rango de trampas y la regla «alguno» de
``vigilancia_activa`` (interpretación provisional, pendiente de confirmación).
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, cast

import pytest

from sigat_api.compartido.errores import NoImplementado
from sigat_api.compartido.tipos import Actor, Cliente, RolCodigo
from sigat_api.modules.concepto.repositorio import RepositorioConcepto
from sigat_api.modules.concepto.servicio import (
    DatosCultivo,
    ServicioConcepto,
    armar_cultivo,
    datos_cultivo,
    rango_trampas,
)

ANA = Actor(usua_id=2, rol=RolCodigo.PRODUCTOR, disp_id=None, cliente=Cliente.WEB)
T1 = datetime(2026, 10, 8, 14, 0, tzinfo=UTC)
T2 = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)


def _fila(lote_id: int, **cambios: Any) -> dict[str, Any]:
    fila: dict[str, Any] = {
        "lote_id": lote_id,
        "lote_descripcion": f"Lote {lote_id}",
        "cultivo": "Durazno",
        "vigilancia_activa": False,
        "mtd": None,
        "concepto": None,
        "ultima_visita": None,
        "ultima_aplicacion": None,
        "cosecha_esperada": None,
        "volumen_esperado": None,
        "trampas": 0,
        "primera_trampa": None,
        "ultima_trampa": None,
    }
    fila.update(cambios)
    return fila


# ------------------------------------------------------------------ rango de trampas
@pytest.mark.parametrize(
    ("trampas", "primera", "ultima", "esperado"),
    [
        (0, None, None, None),
        (1, "54125-R1-1", "54125-R1-1", "54125-R1-1"),
        (4, "54125-R1-1", "54125-R1-7", "54125-R1-1 a 54125-R1-7"),
        (2, "54125-R1-3", "54125-R1-3", "54125-R1-3"),
    ],
)
def test_rango_trampas(trampas: int, primera: str | None, ultima: str | None, esperado: str | None) -> None:
    assert rango_trampas(trampas, primera, ultima) == esperado


# ------------------------------------------------------------------ datos del cultivo
def test_sin_lotes_no_inventa_nada() -> None:
    datos = datos_cultivo([])
    assert datos == DatosCultivo(
        cultivo=None, vigilancia_activa=False, ultima_visita=None, ultima_aplicacion=None, lotes=[]
    )


def test_datos_por_lote_y_agregados() -> None:
    datos = datos_cultivo(
        [
            _fila(
                11,
                vigilancia_activa=True,
                mtd=Decimal("0.360000"),
                concepto="no_emitido",
                ultima_visita=T1,
                ultima_aplicacion=T2,
                cosecha_esperada=date(2026, 11, 15),
                volumen_esperado=Decimal("850.000"),
                trampas=4,
                primera_trampa="54125-R1-1",
                ultima_trampa="54125-R1-7",
            ),
            _fila(12, ultima_visita=T2, ultima_aplicacion=T1),
        ]
    )
    assert datos.cultivo == "Durazno"
    assert datos.vigilancia_activa is True  # alguno de los lotes con periodo abierto
    assert datos.ultima_visita == T1
    assert datos.ultima_aplicacion == T1
    primero, segundo = datos.lotes
    assert (primero.lote_id, primero.mtd, primero.concepto) == (11, Decimal("0.360000"), "no_emitido")
    assert primero.rango_trampas == "54125-R1-1 a 54125-R1-7"
    assert (primero.cosecha_esperada, primero.volumen_esperado) == (date(2026, 11, 15), Decimal("850.000"))
    assert segundo.mtd is None
    assert segundo.rango_trampas is None


def test_vigilancia_inactiva_si_ningun_lote_tiene_periodo_abierto() -> None:
    assert datos_cultivo([_fila(11), _fila(12)]).vigilancia_activa is False


def test_cultivo_nulo_si_los_lotes_tienen_especies_distintas_o_ninguna() -> None:
    assert datos_cultivo([_fila(11), _fila(12, cultivo="Manzana")]).cultivo is None
    assert datos_cultivo([_fila(11, cultivo=None)]).cultivo is None
    # Lotes sin especie no cambian la de los demás.
    assert datos_cultivo([_fila(11), _fila(12, cultivo=None)]).cultivo == "Durazno"


def test_armar_cultivo_no_elige_un_mtd_entre_lotes() -> None:
    datos = datos_cultivo([_fila(11, mtd=Decimal("0.36")), _fila(12, mtd=Decimal("0.07"))])
    cultivo = armar_cultivo(datos, lotes_revisados=3)
    assert cultivo.ultimo_mtd is None
    assert [lote.mtd for lote in cultivo.lotes] == [Decimal("0.36"), Decimal("0.07")]
    assert cultivo.lotes_revisados == 3


# ------------------------------------------------------------------ servicio
class RepoFalso:
    def __init__(self, filas: list[dict[str, Any]], por_responder: int = 0) -> None:
        self.filas = filas
        self.por_responder = por_responder
        self.consultas: list[tuple[str, int]] = []

    async def cultivo_lotes(self, usua_id: int) -> list[dict[str, Any]]:
        self.consultas.append(("cultivo_lotes", usua_id))
        return self.filas

    async def planificaciones_por_responder(self, usua_id: int) -> int:
        self.consultas.append(("planificaciones_por_responder", usua_id))
        return self.por_responder


def _servicio(repo: RepoFalso) -> ServicioConcepto:
    return ServicioConcepto(cast(RepositorioConcepto, repo))


async def test_cultivo_productor_sigue_en_501_por_lotes_revisados() -> None:
    repo = RepoFalso([_fila(11)])
    with pytest.raises(NoImplementado, match="lotes_revisados"):
        await _servicio(repo).cultivo_productor(ANA)
    assert repo.consultas == []  # no consulta la base para luego responder 501


async def test_datos_cultivo_consulta_solo_los_lotes_del_actor() -> None:
    repo = RepoFalso([_fila(11)])
    datos = await _servicio(repo).datos_cultivo(ANA)
    assert [lote.lote_id for lote in datos.lotes] == [11]
    assert repo.consultas == [("cultivo_lotes", ANA.usua_id)]


async def test_inicio_productor() -> None:
    repo = RepoFalso([_fila(11, ultima_visita=T2), _fila(12, ultima_visita=T1)], por_responder=2)
    inicio = await _servicio(repo).inicio_productor(ANA)
    assert (inicio.lotes, inicio.planificaciones_por_responder, inicio.ultima_visita) == (2, 2, T1)
    assert ("planificaciones_por_responder", ANA.usua_id) in repo.consultas


async def test_inicio_productor_sin_lotes_ni_planificaciones() -> None:
    inicio = await _servicio(RepoFalso([])).inicio_productor(ANA)
    assert (inicio.lotes, inicio.planificaciones_por_responder, inicio.ultima_visita) == (0, 0, None)
