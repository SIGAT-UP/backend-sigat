"""Receptor, clasificador y encolador (Arquitectura §6.3)."""

from datetime import datetime
from uuid import UUID

from sigat_api.compartido.errores import NoImplementado, Prohibido
from sigat_api.compartido.tipos import Actor, ClasificacionOperacion
from sigat_api.config import Configuracion
from sigat_api.infra.cola.cola import Cola
from sigat_api.infra.reloj import Reloj
from sigat_api.modules.sincronizacion import esquemas as e
from sigat_api.modules.sincronizacion.puertos import PuertoRegistro, PuertoResultadoPlanificacion
from sigat_api.modules.sincronizacion.repositorio import RepositorioSincronizacion


class ServicioSincronizacion:
    def __init__(
        self,
        repo: RepositorioSincronizacion,
        registro: PuertoRegistro,
        planificacion: PuertoResultadoPlanificacion,
        cola: Cola,
        reloj: Reloj,
        cfg: Configuracion,
    ) -> None:
        self._repo = repo
        self._registro = registro
        self._planificacion = planificacion
        self._cola = cola
        self._reloj = reloj
        self._cfg = cfg

    async def recibir(self, actor: Actor, lote: e.LoteSincronizacion) -> e.RespuestaLote:
        """Procesa el lote EN ORDEN, cada operación en su propio SAVEPOINT (una que falla no
        tumba a las demás; el resultado parcial es normal, ADR-04).

        Por operación:
        1. ``lote.disp_id`` == ``actor.disp_id`` y dispositivo activo; si no -> 403 para TODO el lote.
        2. Recalcular ``hash_contenido`` (huella.py); si no coincide con el enviado -> rechazada
           ``HUELLA_INVALIDA`` (el cliente serializó distinto: error de programación, no de usuario).
        3. Idempotencia R-T4: ¿existe (disp_id, cliente_id)? mismo hash -> ``idempotente_repetida``
           devolviendo el resultado ORIGINAL; distinto -> ``conflicto_contenido``. Ambos en recepcion_sync.
        4. R-T6: |deriva| > SIGAT_SYNC_UMBRAL_DERIVA_RELOJ_SEG y no ``confirma_deriva_reloj`` -> ``revisar``.
        5. Insertar operacion_sync y delegar en Registro (o Planificación para planificacion_lote).
        6. Por cada periodo afectado: encolar ``reprocesar_periodo`` con clave única por peri_id
           (ADR-12: el dato primero; el reproceso no bloquea la respuesta).
        7. Responder con ``reintentable=false`` salvo error técnico (excepción no de dominio).
        Al final: actualizar disp_ultima_sync (disparador fn_dispositivo_sync) y devolver cursor.
        """
        raise NoImplementado("Recepción del lote de sincronización")

    async def pendientes(
        self, actor: Actor, clasificaciones: list[ClasificacionOperacion]
    ) -> list[e.OperacionPendiente]:
        raise NoImplementado("Operaciones pendientes de decisión")

    async def resolver(self, actor: Actor, oper_id: int, s: e.ResolucionOperacion) -> e.ResultadoOperacion:
        """Solo el autor de la operación o un agrónomo del predio. 'confirmar' aplica el payload
        guardado como alta; 'descartar' deja constancia. Ambas crean operación con oper_resuelve_oper_id."""
        raise NoImplementado("Resolución de operación")

    async def cambios(self, actor: Actor, desde: str | None, limite: int) -> e.Cambios:
        raise NoImplementado("Cambios del servidor")


class RegistradorOperacionesEnLinea:
    """Implementa ``registro.puertos.PuertoOperaciones``: las escrituras EN LÍNEA (web) también
    necesitan su fila en ``operacion_sync`` (la BD exige ``oper_id`` y ``disp_id``). Usa el
    dispositivo 'otro' registrado en el login de la sesión web; ``cliente_id`` = uuid4 nuevo y
    la clasificación la decide Registro igual que en el sync."""

    def __init__(self, repo: RepositorioSincronizacion) -> None:
        self._repo = repo

    async def registrar_operacion_en_linea(
        self,
        actor: Actor,
        entidad: str,
        accion: str,
        registro_id: str,
        version: int,
        datos: dict[str, object],
        t_captura: datetime,
    ) -> int:
        raise NoImplementado("Operación en línea")


class ServicioDispositivos:
    """Implementa ``identidad.puertos.PuertoDispositivos``."""

    def __init__(self, repo: RepositorioSincronizacion) -> None:
        self._repo = repo

    async def registrar_o_actualizar(
        self, disp_id: UUID | None, plataforma: str, version_app: str | None, nombre: str | None, usua_id: int
    ) -> UUID:
        """Si ``disp_id`` existe y está activo: actualiza versión/nombre. Si está de baja: 403
        ``DISPOSITIVO_INACTIVO``. Si no viene: crea uno nuevo. Política de dispositivo compartido
        entre usuarios: decisión abierta n.º 4 de la BD v8 (no se inventa).

        Un ``disp_id`` desconocido (p. ej. de otra instalación) o de otra plataforma no se
        reutiliza: se registra un dispositivo nuevo."""
        if disp_id is not None:
            actual = await self._repo.dispositivo(disp_id)
            if actual is not None and not actual["disp_activo"]:
                raise Prohibido(
                    "Este dispositivo fue dado de baja. Contacte al administrador.",
                    codigo="DISPOSITIVO_INACTIVO",
                )
            if actual is None or actual["disp_plataforma"] != plataforma:
                disp_id = None
        return await self._repo.upsert_dispositivo(disp_id, plataforma, version_app, nombre)
