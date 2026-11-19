"""POST /aplicaciones y POST /cosechas (HU-01): reglas del alta en línea del productor."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from sigat_api.compartido.errores import Conflicto, NoEncontrado, Prohibido, ReglaNegocio
from sigat_api.compartido.tipos import Actor, ClasificacionOperacion, Cliente, RolCodigo
from sigat_api.modules.registro import esquemas as e
from sigat_api.modules.registro.servicio import ServicioRegistro
from sigat_api.modules.registro.validador import ValidadorInvariantes
from sigat_api.modules.sincronizacion.servicio import RegistradorOperacionesEnLinea

AHORA = datetime(2026, 11, 19, 15, 0, tzinfo=UTC)
DISP = UUID("0190f5b0-0000-7000-8000-0000000000aa")
PRODUCTOR = 7
LOTE = 42
OPER_ID = 501


class RepoFalso:
    def __init__(self) -> None:
        self.originales: dict[UUID, dict[str, Any]] = {}
        self.insertadas: list[tuple[str, dict[str, Any]]] = []

    async def autorreporte_original(self, entidad: str, registro_id: UUID) -> dict[str, Any] | None:
        return self.originales.get(registro_id)

    async def insertar_version(self, entidad: str, fila: dict[str, Any]) -> UUID:
        self.insertadas.append((entidad, fila))
        return uuid4()

    async def aplicacion_vigente(self, registro_id: UUID) -> dict[str, Any]:
        return _aplicacion_vigente(registro_id)

    async def cosecha_vigente(self, registro_id: UUID) -> dict[str, Any]:
        return _cosecha_vigente(registro_id)


class ConfiguracionFalsa:
    def __init__(self) -> None:
        self.visible = True
        self.activo = True

    async def lote_visible(self, usua_id: int, lote_id: int) -> bool:
        return self.visible

    async def lote_activo_en(self, lote_id: int, instante: datetime) -> bool:
        return self.activo


class OperacionesFalsas:
    def __init__(self) -> None:
        self.registradas: list[dict[str, Any]] = []

    async def registrar_operacion_en_linea(self, actor: Actor, entidad: str, accion: str, registro_id: str,
                                           version: int, datos: dict[str, object], t_captura: datetime) -> int:  # fmt: skip
        self.registradas.append(
            {"entidad": entidad, "accion": accion, "registro_id": registro_id, "version": version,
             "datos": datos, "t_captura": t_captura}
        )  # fmt: skip
        return OPER_ID


class RelojFijo:
    def ahora(self) -> datetime:
        return AHORA


def _actor(rol: RolCodigo = RolCodigo.PRODUCTOR, usua_id: int = PRODUCTOR) -> Actor:
    return Actor(usua_id=usua_id, rol=rol, disp_id=DISP, cliente=Cliente.WEB)


def _servicio() -> tuple[ServicioRegistro, RepoFalso, ConfiguracionFalsa, OperacionesFalsas]:
    repo, config, operaciones = RepoFalso(), ConfiguracionFalsa(), OperacionesFalsas()
    validador = ValidadorInvariantes(config, repo)  # type: ignore[arg-type]
    servicio = ServicioRegistro(
        repo,  # type: ignore[arg-type]
        validador,
        operaciones=operaciones,  # type: ignore[arg-type]
        configuracion=config,  # type: ignore[arg-type]
        reloj=RelojFijo(),
    )
    return servicio, repo, config, operaciones


def _nueva_aplicacion(**cambios: Any) -> e.NuevaAplicacion:
    datos: dict[str, Any] = {
        "apli_registro_id": uuid4(),
        "lote_id": LOTE,
        "apli_producto_texto": "Cipermetrina",
        "apli_dosis": Decimal("2.0"),
        "apli_dosis_uni_id": 3,
        "apli_area_tratada": Decimal("1.2"),
        "apli_area_uni_id": 2,
        "apli_responsable_nombre": "María Rodríguez",
        "t_observacion": AHORA - timedelta(hours=2),
    }
    datos.update(cambios)
    return e.NuevaAplicacion(**datos)


def _nueva_cosecha(**cambios: Any) -> e.NuevaCosecha:
    datos: dict[str, Any] = {
        "cose_registro_id": uuid4(),
        "lote_id": LOTE,
        "cose_fecha_esperada": date(2026, 12, 15),
        "cose_volumen_esperado": Decimal("500"),
        "cose_volumen_uni_id": 1,
        "t_observacion": AHORA - timedelta(hours=2),
    }
    datos.update(cambios)
    return e.NuevaCosecha(**datos)


def _aplicacion_vigente(registro_id: UUID) -> dict[str, Any]:
    return {
        "apli_id": uuid4(), "apli_registro_id": registro_id, "apli_version": 1, "lote_id": LOTE,
        "lote_descripcion": "Lote 2 · Centro", "prof_id": None, "producto": "Cipermetrina",
        "apli_dosis": Decimal("2.0"), "dosis_unidad": "mL/L", "apli_area_tratada": Decimal("1.2"),
        "area_unidad": "ha", "responsable": "María Rodríguez", "apli_observaciones": None,
        "linaje": "autorreporte", "t_observacion": AHORA, "t_captura": AHORA, "t_sincronizacion": AHORA,
        "anulada": False,
    }  # fmt: skip


def _cosecha_vigente(registro_id: UUID) -> dict[str, Any]:
    return {
        "cose_id": uuid4(), "cose_registro_id": registro_id, "cose_version": 1, "lote_id": LOTE,
        "lote_descripcion": "Lote 2 · Centro", "cose_fecha_esperada": date(2026, 12, 15),
        "cose_volumen_esperado": Decimal("500"), "cose_fecha_real": None, "cose_volumen_real": None,
        "unidad": "kg", "cose_metodo_registro": None, "cose_observaciones": None, "linaje": "autorreporte",
        "t_observacion": AHORA, "anulada": False,
    }  # fmt: skip


def _original(s: e.NuevaAplicacion, usua_id: int = PRODUCTOR) -> dict[str, Any]:
    return {
        **s.model_dump(exclude={"apli_registro_id", "t_observacion"}),
        "apli_t_observacion": s.t_observacion,
        "usua_id": usua_id,
    }


@pytest.mark.regla
async def test_alta_de_aplicacion_registra_la_operacion_y_la_version_1_como_autorreporte() -> None:
    servicio, repo, _, operaciones = _servicio()
    s = _nueva_aplicacion()

    respuesta = await servicio.registrar_aplicacion(_actor(), s)

    [operacion] = operaciones.registradas
    assert operacion["entidad"] == "aplicacion_fitosanitaria"
    assert (operacion["accion"], operacion["version"]) == ("crear", 1)
    assert operacion["registro_id"] == str(s.apli_registro_id)
    assert operacion["datos"]["apli_dosis"] == "2.0"
    assert operacion["t_captura"] == AHORA
    [(entidad, fila)] = repo.insertadas
    assert entidad == "aplicacion_fitosanitaria"
    assert fila["apli_linaje"] == "autorreporte"
    assert (fila["apli_version"], fila["apli_registro_id"]) == (1, s.apli_registro_id)
    assert (fila["oper_id"], fila["disp_id"], fila["usua_id"]) == (OPER_ID, DISP, PRODUCTOR)
    assert (fila["apli_t_observacion"], fila["apli_t_captura"]) == (s.t_observacion, AHORA)
    assert respuesta.apli_registro_id == s.apli_registro_id


@pytest.mark.regla
async def test_alta_de_cosecha_registra_la_operacion_y_la_version_1_como_autorreporte() -> None:
    servicio, repo, _, operaciones = _servicio()
    s = _nueva_cosecha()

    respuesta = await servicio.registrar_cosecha(_actor(), s)

    assert [o["entidad"] for o in operaciones.registradas] == ["cosecha"]
    [(entidad, fila)] = repo.insertadas
    assert entidad == "cosecha"
    assert (fila["cose_linaje"], fila["cose_version"], fila["oper_id"]) == ("autorreporte", 1, OPER_ID)
    assert fila["cose_fecha_esperada"] == date(2026, 12, 15)
    assert respuesta.cose_registro_id == s.cose_registro_id


@pytest.mark.regla
async def test_reenviar_el_mismo_alta_no_duplica() -> None:
    servicio, repo, _, operaciones = _servicio()
    s = _nueva_aplicacion()
    repo.originales[s.apli_registro_id] = _original(s)

    respuesta = await servicio.registrar_aplicacion(_actor(), s)

    assert operaciones.registradas == []
    assert repo.insertadas == []
    assert respuesta.apli_registro_id == s.apli_registro_id


@pytest.mark.regla
@pytest.mark.parametrize("cambio", [{"apli_dosis": Decimal("3")}, {"usua_id": 99}])
async def test_mismo_identificador_con_otro_contenido_o_autor_es_conflicto(cambio: dict[str, Any]) -> None:
    servicio, repo, _, operaciones = _servicio()
    s = _nueva_aplicacion()
    repo.originales[s.apli_registro_id] = {**_original(s), **cambio}

    with pytest.raises(Conflicto) as error:
        await servicio.registrar_aplicacion(_actor(), s)

    assert error.value.codigo == "REGISTRO_EXISTENTE"
    assert operaciones.registradas == []


@pytest.mark.regla
async def test_lote_ajeno_o_inexistente_responde_404_sin_registrar() -> None:
    servicio, repo, config, operaciones = _servicio()
    config.visible = False

    with pytest.raises(NoEncontrado) as error:
        await servicio.registrar_cosecha(_actor(), _nueva_cosecha())

    assert error.value.codigo == "LOTE_NO_ENCONTRADO"
    assert (operaciones.registradas, repo.insertadas) == ([], [])


@pytest.mark.regla
async def test_fecha_futura_se_rechaza() -> None:
    servicio, _, _, operaciones = _servicio()

    with pytest.raises(ReglaNegocio) as error:
        await servicio.registrar_aplicacion(
            _actor(), _nueva_aplicacion(t_observacion=AHORA + timedelta(minutes=1))
        )

    assert error.value.codigo == "FECHA_FUTURA"
    assert operaciones.registradas == []


@pytest.mark.regla
async def test_lote_inactivo_en_la_fecha_se_rechaza() -> None:
    servicio, _, config, _ = _servicio()
    config.activo = False

    with pytest.raises(ReglaNegocio) as error:
        await servicio.registrar_cosecha(_actor(), _nueva_cosecha())

    assert error.value.codigo == "LOTE_INACTIVO"


@pytest.mark.regla
async def test_un_rol_oficial_no_registra_autorreportes() -> None:
    servicio, _, _, _ = _servicio()

    with pytest.raises(ReglaNegocio) as error:
        await servicio.registrar_aplicacion(_actor(RolCodigo.TECNICO), _nueva_aplicacion())

    assert error.value.codigo == "LINAJE_NO_PERMITIDO"


@pytest.mark.parametrize(
    ("cambios", "mensaje"),
    [
        ({"apli_producto_texto": " "}, "producto"),
        ({"apli_responsable_nombre": None}, "responsable"),
        ({"t_observacion": datetime(2026, 11, 19, 10, 0)}, "timezone"),  # noqa: DTZ001
    ],
)
def test_alta_de_aplicacion_valida_los_mismos_check_de_la_bd(cambios: dict[str, Any], mensaje: str) -> None:
    with pytest.raises(ValidationError, match=mensaje):
        _nueva_aplicacion(**cambios)


def test_fecha_y_volumen_reales_de_cosecha_van_juntos() -> None:
    with pytest.raises(ValidationError, match="reales"):
        _nueva_cosecha(cose_fecha_real=date(2026, 12, 20))
    cerrada = _nueva_cosecha(cose_fecha_real=date(2026, 12, 20), cose_volumen_real=Decimal("480"))
    assert cerrada.cose_volumen_real == Decimal("480")


class RepoSincronizacionFalso:
    def __init__(self) -> None:
        self.filas: list[dict[str, Any]] = []

    async def insertar_operacion(self, fila: dict[str, Any]) -> int:
        self.filas.append(fila)
        return len(self.filas)


async def test_la_operacion_en_linea_usa_el_dispositivo_de_la_sesion_y_una_huella_estable() -> None:
    repo = RepoSincronizacionFalso()
    registrador = RegistradorOperacionesEnLinea(repo)  # type: ignore[arg-type]
    registro_id = str(uuid4())
    datos: dict[str, object] = {"lote_id": LOTE, "apli_dosis": "2.0"}

    for _ in range(2):
        await registrador.registrar_operacion_en_linea(
            _actor(), "aplicacion_fitosanitaria", "crear", registro_id, 1, datos, AHORA
        )

    primera, segunda = repo.filas
    assert (primera["disp_id"], primera["usua_id"]) == (DISP, PRODUCTOR)
    assert primera["clasificacion"] == ClasificacionOperacion.ALTA_NUEVA
    assert primera["registro_id"] == UUID(registro_id)
    assert len(primera["hash"]) == 64
    assert primera["hash"] == segunda["hash"]
    assert primera["cliente_id"] != segunda["cliente_id"]


async def test_sin_dispositivo_en_la_sesion_no_se_registra_la_operacion() -> None:
    repo = RepoSincronizacionFalso()
    actor = Actor(usua_id=PRODUCTOR, rol=RolCodigo.PRODUCTOR, disp_id=None, cliente=Cliente.WEB)

    with pytest.raises(Prohibido):
        await RegistradorOperacionesEnLinea(repo).registrar_operacion_en_linea(  # type: ignore[arg-type]
            actor, "cosecha", "crear", str(uuid4()), 1, {}, AHORA
        )
    assert repo.filas == []
