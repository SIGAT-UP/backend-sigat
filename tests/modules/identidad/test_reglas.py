"""Reglas del inicio de sesión (módulo identidad). No necesitan base de datos: el
repositorio y el registro de dispositivos se reemplazan por dobles en memoria."""

import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr

from sigat_api.compartido.errores import DemasiadasSolicitudes, NoAutenticado, Prohibido, ReglaNegocio
from sigat_api.compartido.tipos import Cliente, Plataforma, RolCodigo
from sigat_api.config import Configuracion
from sigat_api.infra.seguridad import contrasenas
from sigat_api.infra.seguridad.tokens import ServicioTokens, hash_refresco
from sigat_api.modules.identidad import esquemas as e
from sigat_api.modules.identidad.servicio import MENSAJE_CREDENCIALES, ServicioAutenticacion

# Contraseña aleatoria en cada ejecución: no hay credenciales escritas en el repositorio.
CLAVE = secrets.token_urlsafe(12)
HASH = contrasenas.generar_hash(CLAVE)


def _usuario(usua_id: int, usuario: str, rol: str, **extra: Any) -> dict[str, Any]:
    base = {
        "usua_id": usua_id,
        "usua_usuario": usuario,
        "usua_contrasena": HASH,
        "usua_proveedor": "local",
        "usua_requiere_reinicio": False,
        "usua_eliminado_en": None,
        "pers_cc": 1000 + usua_id,
        "pers_nombre": "Ana María",
        "pers_apellido": "Pérez",
        "pers_correo": f"{usuario}@sigat.test",
        "rol_codigo": rol,
        "rol_descripcion": rol.title(),
        "estado": "activo",
        "rol_coherente": True,
        "predio_nombre": None,
        "predios": 0,
    }
    base.update(extra)
    return base


class RepoFalso:
    """Doble en memoria de ``RepositorioIdentidad`` con lo que usa la autenticación."""

    def __init__(self, usuarios: list[dict[str, Any]]) -> None:
        self.usuarios = {u["usua_id"]: u for u in usuarios}
        self.intentos: list[tuple[str, bool, datetime]] = []
        self.sesiones: dict[str, dict[str, Any]] = {}
        self.restablecimientos: dict[str, dict[str, Any]] = {}
        self.actor: int | None = None
        self.siguiente_rest = 1

    async def fijar_actor(self, usua_id: int) -> None:
        self.actor = usua_id

    async def buscar_para_login(self, valor: str) -> dict[str, Any] | None:
        v = valor.strip().lower()
        for u in self.usuarios.values():
            if u["usua_eliminado_en"] is None and v in (u["usua_usuario"].lower(), u["pers_correo"].lower()):
                return u
        return None

    async def usuario_por_id(self, usua_id: int) -> dict[str, Any] | None:
        return self.usuarios.get(usua_id)

    async def registrar_acceso(self, usua_id: int, momento: datetime, nuevo_hash: str | None = None) -> None:
        self.usuarios[usua_id]["ultimo_acceso"] = momento

    async def fallos_recientes(self, clave: str, desde: datetime) -> int:
        n = 0
        for c, ok, t in self.intentos:
            if c == clave:
                n = 0 if ok else (n + 1 if t >= desde else n)
        return n

    async def registrar_intento(self, claves: list[str], exito: bool) -> None:
        for c in claves:
            self.intentos.append((c, exito, datetime.now(UTC)))

    async def guardar_sesion_refresco(
        self, usua_id: int, disp_id: UUID, hash_token: str, familia: UUID, expira: datetime, cliente: str
    ) -> None:
        self.sesiones[hash_token] = {
            "usua_id": usua_id,
            "disp_id": disp_id,
            "sesr_familia": familia,
            "sesr_cliente": cliente,
            "sesr_expira_en": expira,
            "sesr_usado_en": None,
            "sesr_revocado_en": None,
        }

    async def consumir_sesion_refresco(self, hash_token: str, ahora: datetime) -> dict[str, Any] | None:
        s = self.sesiones.get(hash_token)
        if s is None:
            return None
        if s["sesr_revocado_en"] and not s["sesr_usado_en"]:
            return {**s, "estado": "revocada"}
        if s["sesr_usado_en"] is None:
            s["sesr_usado_en"] = ahora
            return {**s, "estado": "valida"}
        for otra in self.sesiones.values():
            if otra["sesr_familia"] == s["sesr_familia"] and otra["sesr_revocado_en"] is None:
                otra["sesr_revocado_en"] = ahora
        return {**s, "estado": "reutilizada"}

    async def revocar_sesiones(
        self, usua_id: int, ahora: datetime, disp_id: UUID | None = None, excepto_disp: UUID | None = None
    ) -> None:
        for s in self.sesiones.values():
            if (
                s["usua_id"] == usua_id
                and (disp_id is None or s["disp_id"] == disp_id)
                and (excepto_disp is None or s["disp_id"] != excepto_disp)
            ):
                s["sesr_revocado_en"] = s["sesr_revocado_en"] or ahora

    async def crear_restablecimiento(self, usua_id: int, hash_token: str, expira: datetime) -> int:
        rest_id = self.siguiente_rest
        self.siguiente_rest += 1
        self.restablecimientos[hash_token] = {
            "rest_id": rest_id, "usua_id": usua_id, "expira": expira, "usado": False, "creado": datetime.now(UTC),
        }  # fmt: skip
        return rest_id

    async def solicitud_reciente(self, usua_id: int, desde: datetime) -> bool:
        return any(
            r["usua_id"] == usua_id and not r["usado"] and r["creado"] >= desde
            for r in self.restablecimientos.values()
        )

    async def administradores_activos(self, excepto: int | None = None) -> list[int]:
        return [
            u["usua_id"]
            for u in self.usuarios.values()
            if u["rol_codigo"] == "ADMINISTRADOR" and u["estado"] == "activo" and u["usua_id"] != excepto
        ]

    async def usar_restablecimiento(self, hash_token: str, ahora: datetime) -> int | None:
        r = self.restablecimientos.get(hash_token)
        if r is None or r["usado"] or r["expira"] <= ahora:
            return None
        r["usado"] = True
        return int(r["usua_id"])

    async def actualizar_contrasena(self, usua_id: int, hash_contrasena: str) -> None:
        self.usuarios[usua_id]["usua_contrasena"] = hash_contrasena


class AvisosFalsos:
    """Doble de ``PuertoAvisos``: guarda los avisos y respeta la clave de evento (no duplica)."""

    def __init__(self) -> None:
        self.avisos: list[dict[str, Any]] = []

    async def emitir(
        self,
        usua_id: int,
        categoria: str,
        titulo: str,
        cuerpo: str,
        evento_clave: str,
        ruta: str | None = None,
        argumento: str | None = None,
    ) -> bool:
        if any(a["usua_id"] == usua_id and a["evento_clave"] == evento_clave for a in self.avisos):
            return False
        self.avisos.append(
            {"usua_id": usua_id, "categoria": categoria, "cuerpo": cuerpo, "evento_clave": evento_clave,
             "ruta": ruta, "argumento": argumento}
        )  # fmt: skip
        return True


class DispositivosFalsos:
    async def registrar_o_actualizar(
        self, disp_id: UUID | None, plataforma: str, version_app: str | None, nombre: str | None, usua_id: int
    ) -> UUID:
        return disp_id or uuid4()


@pytest.fixture
def cfg() -> Configuracion:
    return Configuracion(jwt_secreto=SecretStr(os.environ["SIGAT_JWT_SECRETO"]))


@pytest.fixture
def repo() -> RepoFalso:
    return RepoFalso(
        [
            _usuario(1, "agronomo", "AGRONOMO_SUPERVISOR"),
            _usuario(2, "tecnico", "TECNICO"),
            _usuario(3, "inactivo", "PRODUCTOR", estado="inactivo"),
            _usuario(4, "incompleto", "ADMINISTRADOR", rol_coherente=False),
            _usuario(5, "productor", "PRODUCTOR", predio_nombre="Finca El Mirador", predios=2),
            _usuario(6, "admin.uno", "ADMINISTRADOR"),
            _usuario(7, "admin.dos", "ADMINISTRADOR"),
            _usuario(8, "admin.inactivo", "ADMINISTRADOR", estado="inactivo"),
        ]
    )


@pytest.fixture
def avisos() -> AvisosFalsos:
    return AvisosFalsos()


@pytest.fixture
def svc(repo: RepoFalso, cfg: Configuracion, avisos: AvisosFalsos) -> ServicioAutenticacion:
    return ServicioAutenticacion(repo, DispositivosFalsos(), ServicioTokens(cfg), cfg, avisos=avisos)  # type: ignore[arg-type]


def _login(usuario: str, clave: str = CLAVE, cliente: Cliente = Cliente.WEB) -> e.SolicitudLogin:
    return e.SolicitudLogin(usuario=usuario, contrasena=SecretStr(clave), cliente=cliente)


@pytest.mark.regla
async def test_identidad_01(svc: ServicioAutenticacion) -> None:
    """login con usuario inexistente, clave errada o cuenta inactiva da el MISMO mensaje."""
    for usuario, clave in (("nadie", CLAVE), ("agronomo", "mala-clave"), ("inactivo", CLAVE)):
        with pytest.raises(NoAutenticado) as err:
            await svc.iniciar_sesion(_login(usuario, clave), "10.0.0.1")
        assert err.value.detalle == MENSAJE_CREDENCIALES
        assert err.value.codigo == "CREDENCIALES_INVALIDAS"


@pytest.mark.regla
async def test_identidad_02(svc: ServicioAutenticacion) -> None:
    """cuenta TECNICO no puede iniciar sesión con cliente=web; con movil sí."""
    with pytest.raises(Prohibido) as err:
        await svc.iniciar_sesion(_login("tecnico"), None)
    assert err.value.codigo == "ROL_SOLO_MOVIL"
    r = await svc.iniciar_sesion(_login("tecnico", cliente=Cliente.MOVIL), None)
    assert r.respuesta.user.rol is RolCodigo.TECNICO
    assert r.respuesta.token_refresco  # el móvil recibe el refresco en el cuerpo


@pytest.mark.regla
async def test_identidad_03(svc: ServicioAutenticacion) -> None:
    """rol sin sus datos completos (fila hija) no inicia sesión (S-01)."""
    with pytest.raises(Prohibido) as err:
        await svc.iniciar_sesion(_login("incompleto"), None)
    assert err.value.codigo == "CUENTA_INCOMPLETA"


@pytest.mark.regla
async def test_identidad_04(svc: ServicioAutenticacion, repo: RepoFalso) -> None:
    """refresco reutilizado revoca toda la familia."""
    r = await svc.iniciar_sesion(_login("agronomo"), None)
    primero = r.token_refresco
    segundo = (await svc.refrescar(primero)).token_refresco
    with pytest.raises(NoAutenticado) as err:
        await svc.refrescar(primero)
    assert err.value.codigo == "REFRESCO_REUTILIZADO"
    with pytest.raises(NoAutenticado) as err:
        await svc.refrescar(segundo)  # el legítimo también queda revocado
    assert err.value.codigo == "REFRESCO_REVOCADO"


@pytest.mark.regla
async def test_identidad_05(svc: ServicioAutenticacion, repo: RepoFalso) -> None:
    """recuperación responde igual exista o no la cuenta; solo guarda el hash del token."""
    await svc.solicitar_recuperacion(e.SolicitudRecuperacion(identificador="nadie@sigat.test"))
    assert repo.restablecimientos == {}
    await svc.solicitar_recuperacion(e.SolicitudRecuperacion(identificador="agronomo"))
    (clave,) = repo.restablecimientos
    assert len(clave) == 64  # SHA-256 en hexadecimal, nunca el token


@pytest.mark.regla
async def test_identidad_06(svc: ServicioAutenticacion, repo: RepoFalso) -> None:
    """token de recuperación es de uso único y vence; al usarlo se cierran las sesiones."""
    token = "t" * 40
    await repo.crear_restablecimiento(1, hash_refresco(token), datetime.now(UTC) + timedelta(minutes=5))
    sesion = await svc.iniciar_sesion(_login("agronomo"), None)
    await svc.confirmar_recuperacion(
        e.ConfirmacionRecuperacion(token=token, nueva_contrasena=SecretStr("NuevaClave2026"))
    )
    assert contrasenas.verificar("NuevaClave2026", repo.usuarios[1]["usua_contrasena"])
    with pytest.raises(NoAutenticado):
        await svc.refrescar(sesion.token_refresco)
    with pytest.raises(ReglaNegocio):
        await svc.confirmar_recuperacion(
            e.ConfirmacionRecuperacion(token=token, nueva_contrasena=SecretStr("OtraClave20266"))
        )
    vencido = "v" * 40
    await repo.crear_restablecimiento(1, hash_refresco(vencido), datetime.now(UTC) - timedelta(minutes=1))
    with pytest.raises(ReglaNegocio):
        await svc.confirmar_recuperacion(
            e.ConfirmacionRecuperacion(token=vencido, nueva_contrasena=SecretStr("OtraClave20266"))
        )


@pytest.mark.regla
async def test_identidad_07(svc: ServicioAutenticacion, cfg: Configuracion) -> None:
    """el actor sale del token: los reclamos traen el usuario, el rol, el dispositivo y el cliente."""
    r = await svc.iniciar_sesion(_login("agronomo"), None)
    reclamos = ServicioTokens(cfg).verificar_acceso(r.respuesta.token)
    assert reclamos.usua_id == 1
    assert reclamos.rol is RolCodigo.AGRONOMO_SUPERVISOR
    assert reclamos.disp_id == r.respuesta.disp_id
    assert reclamos.cliente is Cliente.WEB


@pytest.mark.regla
async def test_identidad_08(svc: ServicioAutenticacion, cfg: Configuracion) -> None:
    """tras N fallos seguidos del mismo usuario se bloquea el inicio de sesión por la ventana."""
    for _ in range(cfg.login_max_fallos_usuario):
        with pytest.raises(NoAutenticado):
            await svc.iniciar_sesion(_login("agronomo", "mala-clave"), None)
    with pytest.raises(DemasiadasSolicitudes):
        await svc.iniciar_sesion(_login("agronomo"), None)


@pytest.mark.regla
async def test_identidad_09(svc: ServicioAutenticacion) -> None:
    """usuario o correo, sin distinguir mayúsculas; la sesión trae nombre, iniciales y predio."""
    r = await svc.iniciar_sesion(_login("PRODUCTOR@SIGAT.TEST"), None)
    u = r.respuesta.user
    assert (u.usuario, u.nombre, u.iniciales) == ("productor", "Ana María Pérez", "AP")
    assert u.predio_etiqueta == "Finca El Mirador · durazno (+1)"
    assert r.respuesta.token_refresco is None  # web: el refresco va en cookie, no en el cuerpo


@pytest.mark.regla
async def test_identidad_10(svc: ServicioAutenticacion) -> None:
    """el dispositivo enviado por el móvil se conserva entre inicios de sesión."""
    disp = uuid4()
    s = e.SolicitudLogin(
        usuario="tecnico",
        contrasena=SecretStr(CLAVE),
        cliente=Cliente.MOVIL,
        dispositivo=e.DispositivoEntrada(disp_id=disp, plataforma=Plataforma.ANDROID),
    )
    assert (await svc.iniciar_sesion(s, None)).respuesta.disp_id == disp


@pytest.mark.regla
async def test_identidad_11(svc: ServicioAutenticacion, cfg: Configuracion) -> None:
    """el límite de intentos cuenta por cuenta: fallar con el usuario y entrar con el correo lo reinicia."""
    for _ in range(cfg.login_max_fallos_usuario - 1):
        with pytest.raises(NoAutenticado):
            await svc.iniciar_sesion(_login("agronomo", "mala-clave"), None)
    await svc.iniciar_sesion(_login("agronomo@sigat.test"), None)
    for _ in range(cfg.login_max_fallos_usuario - 1):
        with pytest.raises(NoAutenticado):
            await svc.iniciar_sesion(_login("AGRONOMO", "mala-clave"), None)
    assert (await svc.iniciar_sesion(_login("agronomo"), None)).respuesta.user.id == 1


@pytest.mark.regla
async def test_identidad_12(svc: ServicioAutenticacion, avisos: AvisosFalsos) -> None:
    """«olvidé mi contraseña» avisa a CADA administrador activo para que él asigne una clave nueva."""
    await svc.solicitar_recuperacion(e.SolicitudRecuperacion(identificador="agronomo"))
    assert {a["usua_id"] for a in avisos.avisos} == {4, 6, 7}  # el administrador inactivo (8) no
    for a in avisos.avisos:
        assert a["categoria"] == "solicitudes_cuenta"
        assert (a["ruta"], a["argumento"]) == ("/admin/usuarios", "1")
        assert "agronomo" in a["cuerpo"]


@pytest.mark.regla
async def test_identidad_13(svc: ServicioAutenticacion, avisos: AvisosFalsos, repo: RepoFalso) -> None:
    """repetir la solicitud dentro de la ventana no duplica avisos; una cuenta inexistente o inactiva no avisa."""
    for identificador in ("agronomo", "AGRONOMO", "agronomo@sigat.test"):
        await svc.solicitar_recuperacion(e.SolicitudRecuperacion(identificador=identificador))
    assert len(avisos.avisos) == 3  # uno por administrador activo
    assert len(repo.restablecimientos) == 1
    for identificador in ("nadie", "inactivo"):
        await svc.solicitar_recuperacion(e.SolicitudRecuperacion(identificador=identificador))
    assert len(avisos.avisos) == 3


@pytest.mark.regla
async def test_identidad_14(svc: ServicioAutenticacion, repo: RepoFalso) -> None:
    """cambiar la propia contraseña cierra las sesiones de los OTROS dispositivos, no la actual."""
    from sigat_api.compartido.tipos import Actor

    web = await svc.iniciar_sesion(_login("agronomo"), None)
    movil = await svc.iniciar_sesion(_login("agronomo", cliente=Cliente.MOVIL), None)
    actor = Actor(
        usua_id=1, rol=RolCodigo.AGRONOMO_SUPERVISOR, disp_id=web.respuesta.disp_id, cliente=Cliente.WEB
    )
    await svc.cambiar_contrasena(
        actor, e.CambioContrasena(actual=SecretStr(CLAVE), nueva=SecretStr("Nueva-clave-2026"))
    )
    assert (await svc.refrescar(web.token_refresco)).token_refresco
    with pytest.raises(NoAutenticado):
        await svc.refrescar(movil.token_refresco)
