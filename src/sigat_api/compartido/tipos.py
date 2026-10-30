"""Vocabulario compartido. Cada valor coincide EXACTAMENTE con la BD SIGAT v8
(dominios ``sigat.d_*`` y restricciones CHECK). Si la BD cambia, cambia aquí."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class RolCodigo(StrEnum):
    """``rol.rol_codigo``. La web y el móvil traducen a sus propios nombres."""

    ADMINISTRADOR = "ADMINISTRADOR"
    AGRONOMO_SUPERVISOR = "AGRONOMO_SUPERVISOR"
    TECNICO = "TECNICO"
    PRODUCTOR = "PRODUCTOR"


class Cliente(StrEnum):
    """Quién llama. Decide la entrega del token de refresco (cookie o cuerpo)."""

    WEB = "web"
    MOVIL = "movil"


class Linaje(StrEnum):
    """``sigat.d_linaje`` (RN-014)."""

    INSPECCION_OFICIAL = "inspeccion_oficial"
    AUTORREPORTE = "autorreporte"


class EntidadSync(StrEnum):
    """``operacion_sync.oper_entidad`` (CHECK ``operacion_sync_entidad_valida`` v8)."""

    VISITA = "visita"
    LECTURA_TRAMPA = "lectura_trampa"
    APLICACION_FITOSANITARIA = "aplicacion_fitosanitaria"
    COSECHA = "cosecha"
    ETAPA_DECLARADA = "etapa_declarada"
    HALLAZGO = "hallazgo"
    BPA_VERIFICACION = "bpa_verificacion"
    MANEJO_AGRONOMICO = "manejo_agronomico"
    ESTIMACION_PRODUCCION = "estimacion_produccion"
    PLANIFICACION_LOTE = "planificacion_lote"
    EVIDENCIA = "evidencia"  # BD v9: cada foto con su propia operación (registro_id = evid_id)


class AccionSync(StrEnum):
    """``operacion_sync.oper_accion``."""

    CREAR = "crear"
    CORREGIR = "corregir"
    ANULAR = "anular"


class ClasificacionOperacion(StrEnum):
    """``sigat.d_clasificacion_operacion`` (ADR-04). Lo que se GUARDA en operacion_sync."""

    ALTA_NUEVA = "alta_nueva"
    ALTA_RETROACTIVA = "alta_retroactiva"
    CORRECCION = "correccion"
    REVISAR = "revisar"
    RECHAZADA = "rechazada"


class ResultadoSync(StrEnum):
    """Lo que se RESPONDE al cliente por operación. Añade los dos resultados de
    reenvío que la BD registra en ``recepcion_sync.rece_resultado``."""

    ALTA_NUEVA = "alta_nueva"
    ALTA_RETROACTIVA = "alta_retroactiva"
    CORRECCION = "correccion"
    IDEMPOTENTE_REPETIDA = "idempotente_repetida"
    CONFLICTO_CONTENIDO = "conflicto_contenido"
    REVISAR = "revisar"
    RECHAZADA = "rechazada"


class EstadoRevision(StrEnum):
    """``sigat.d_estado_revision`` (visita)."""

    PENDIENTE = "pendiente"
    EN_REVISION = "en_revision"
    ACEPTADO = "aceptado"


class EstadoRevisionLectura(StrEnum):
    """Estado de cada lectura en la vista ``v_lectura_revision`` (BD v9). DERIVADO, no se guarda."""

    SIN_VERIFICAR = "sin_verificar"
    CONFIRMADO = "confirmado"
    CORREGIDO = "corregido"
    RECHAZADO = "rechazado"
    AUTORREPORTE = "autorreporte"


class ResultadoContraste(StrEnum):
    """``sigat.d_resultado_contraste`` (RF-024)."""

    POR_DEBAJO_UMBRAL = "por_debajo_umbral"
    IGUAL_O_SUPERIOR_UMBRAL = "igual_o_superior_umbral"
    SIN_UMBRAL = "sin_umbral"


class ResultadoConcepto(StrEnum):
    """``concepto_aptitud.conc_resultado``."""

    APTO = "apto"
    NO_APTO = "no_apto"
    NO_EMITIDO = "no_emitido"


class EstadoPlanificacion(StrEnum):
    """``planificacion.plan_estado``. El técnico nunca tiene aceptada/rechazada."""

    PENDIENTE = "pendiente"
    ACEPTADA = "aceptada"
    RECHAZADA = "rechazada"
    COMPLETADA = "completada"


class EstadoPlanLote(StrEnum):
    """``planificacion_lote.plal_estado``."""

    PENDIENTE = "pendiente"
    EJECUTADA = "ejecutada"
    NO_EJECUTADA = "no_ejecutada"


class ClaseArchivo(StrEnum):
    """``archivo_adjunto.arch_clase``."""

    FOTO_EVIDENCIA = "foto_evidencia"
    FOTO_PERFIL = "foto_perfil"
    DOCUMENTO_INSTRUCCION = "documento_instruccion"
    IMAGEN_DISENO = "imagen_diseno"


class EstadoArchivo(StrEnum):
    """``archivo_adjunto.arch_estado``."""

    PENDIENTE_CONTENIDO = "pendiente_contenido"
    ALMACENADO = "almacenado"
    RECHAZADO = "rechazado"


class CategoriaNotificacion(StrEnum):
    """``categoria_notificacion.cate_codigo``."""

    ASIGNACION = "asignacion"
    ALERTAS_FITOSANITARIAS = "alertas_fitosanitarias"
    RECORDATORIOS_INSPECCION = "recordatorios_inspeccion"
    AVISOS_PREDIO = "avisos_predio"
    SINCRONIZACION = "sincronizacion"
    SOLICITUDES_CUENTA = "solicitudes_cuenta"  # BD v9.1: «¿Problemas para ingresar?» -> administradores


class Plataforma(StrEnum):
    """``dispositivo.disp_plataforma``. La web se registra como ``otro``."""

    ANDROID = "android"
    IOS = "ios"
    OTRO = "otro"


@dataclass(frozen=True, slots=True)
class Actor:
    """Quién ejecuta la operación. Se deduce SIEMPRE del token, nunca del cuerpo.

    ``usua_id`` se fija en cada transacción como ``sigat.usuario_actual``
    (los disparadores de la BD lo exigen: autoría, auditoría, planificación).
    """

    usua_id: int
    rol: RolCodigo
    disp_id: UUID | None
    cliente: Cliente
    # Momento de emisión del token: se compara con las revocaciones (ver ``infra.db.sesion``).
    emitido_en: datetime | None = None
