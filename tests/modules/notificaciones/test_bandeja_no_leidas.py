"""Bandeja de avisos (decisión del Owner, Sprint 3): solo no leídas, más reciente primero, paginación estable."""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from sigat_api.compartido.tipos import Actor, Cliente, RolCodigo
from sigat_api.modules.notificaciones import servicio as modulo
from sigat_api.modules.notificaciones.servicio import ServicioNotificaciones

USUARIO, OTRO = 1, 2
BASE = datetime(2026, 11, 1, tzinfo=UTC)


class RepoBandeja:
    def __init__(self, filas: list[dict[str, Any]]) -> None:
        self.filas = filas

    async def listar(
        self, usua_id: int, despues_de: tuple[datetime, int] | None, limite: int
    ) -> list[dict[str, Any]]:
        filas = [f for f in self.filas if f["usua_id"] == usua_id and f["noti_leida_en"] is None]
        if despues_de is not None:
            filas = [f for f in filas if (f["noti_creada_en"], f["noti_id"]) < despues_de]
        return sorted(filas, key=lambda f: (f["noti_creada_en"], f["noti_id"]), reverse=True)[:limite]

    async def marcar_leida(self, usua_id: int, noti_id: int, momento: datetime) -> bool:
        for f in self.filas:
            if f["usua_id"] == usua_id and f["noti_id"] == noti_id:
                f["noti_leida_en"] = momento
                return True
        return False


def _aviso(noti_id: int, creada: datetime, usua_id: int = USUARIO, leida: bool = False) -> dict[str, Any]:
    return {
        "noti_id": noti_id, "usua_id": usua_id, "cate_codigo": "asignacion", "noti_titulo": "T",
        "noti_cuerpo": "C", "noti_creada_en": creada, "noti_leida_en": creada if leida else None,
        "noti_destino_ruta": None, "noti_destino_argumento": None,
    }  # fmt: skip


def _actor() -> Actor:
    return Actor(usua_id=USUARIO, rol=RolCodigo.PRODUCTOR, disp_id=None, cliente=Cliente.WEB)


async def _todas(servicio: ServicioNotificaciones, al_pasar_pagina: Any = None) -> list[int]:
    vistos: list[int] = []
    cursor: str | None = None
    while True:
        pagina = await servicio.listar(_actor(), cursor)
        vistos += [n.noti_id for n in pagina.items]
        if pagina.siguiente is None:
            return vistos
        if al_pasar_pagina:
            await al_pasar_pagina()
        cursor = pagina.siguiente


@pytest.fixture
def pagina_de_dos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(modulo, "TAMANO_PAGINA", 2)


@pytest.mark.regla
@pytest.mark.usefixtures("pagina_de_dos")
async def test_solo_no_leidas_del_actor_de_la_mas_reciente_a_la_mas_antigua() -> None:
    repo = RepoBandeja(
        [
            _aviso(1, BASE),
            _aviso(2, BASE + timedelta(days=2)),
            _aviso(3, BASE + timedelta(days=1), leida=True),
            _aviso(4, BASE + timedelta(days=3), usua_id=OTRO),
            _aviso(5, BASE + timedelta(days=1)),
        ]
    )

    assert await _todas(ServicioNotificaciones(repo)) == [2, 5, 1]  # type: ignore[arg-type]


@pytest.mark.regla
@pytest.mark.usefixtures("pagina_de_dos")
async def test_empates_de_fecha_se_ordenan_por_id_sin_repetir_ni_omitir() -> None:
    repo = RepoBandeja([_aviso(i, BASE) for i in range(1, 6)])

    assert await _todas(ServicioNotificaciones(repo)) == [5, 4, 3, 2, 1]  # type: ignore[arg-type]


@pytest.mark.regla
@pytest.mark.usefixtures("pagina_de_dos")
async def test_marcar_leidos_entre_paginas_no_desplaza_la_bandeja() -> None:
    repo = RepoBandeja([_aviso(i, BASE + timedelta(hours=i)) for i in range(1, 7)])
    servicio = ServicioNotificaciones(repo)  # type: ignore[arg-type]

    async def leer_lo_ya_visto() -> None:
        for f in repo.filas:
            if f["noti_id"] >= 5:
                await servicio.marcar_leida(_actor(), f["noti_id"])

    assert await _todas(servicio, leer_lo_ya_visto) == [6, 5, 4, 3, 2, 1]
    assert [f["noti_id"] for f in repo.filas if f["noti_leida_en"] is None] == [1, 2, 3, 4]
    assert len(repo.filas) == 6  # leer no borra


@pytest.mark.regla
async def test_un_cursor_ilegible_vuelve_a_la_primera_pagina() -> None:
    repo = RepoBandeja([_aviso(1, BASE)])

    pagina = await ServicioNotificaciones(repo).listar(_actor(), "no-es-un-cursor")  # type: ignore[arg-type]

    assert [n.noti_id for n in pagina.items] == [1]
