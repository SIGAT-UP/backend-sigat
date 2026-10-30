"""Configuración del servicio, leída SOLO de variables de entorno (prefijo ``SIGAT_``).

Ningún valor sensible tiene valor por defecto real. Ver ``.env.example``.
"""

from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracion(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SIGAT_", env_file=".env", extra="ignore")

    # --- Aplicación
    entorno: Literal["desarrollo", "pruebas", "produccion"] = "desarrollo"
    depuracion: bool = False
    prefijo_api: str = "/api/v1"
    zona_horaria_predeterminada: str = "America/Bogota"
    version_minima_app: str | None = None

    # --- Base de datos SIGAT v9
    db_url: str = "postgresql+asyncpg://usuario:clave@localhost:5432/sigat"  # pragma: allowlist secret
    db_esquema: str = "sigat"
    db_pool_tamano: int = 10
    db_pool_extra: int = 5
    db_timeout_sentencia_ms: int = 15_000

    # --- Tokens
    jwt_secreto: SecretStr = SecretStr("")
    jwt_algoritmo: str = "HS256"
    jwt_emisor: str = "sigat-durazno-api"
    jwt_audiencia: str = "sigat-durazno"
    token_acceso_minutos: int = 15
    token_refresco_dias_web: int = 1
    token_refresco_dias_movil: int = 30
    recuperacion_minutos: int = 30
    login_max_fallos_usuario: int = 5
    login_max_fallos_ip: int = 30
    login_ventana_minutos: int = 15

    # --- Web
    cors_origenes: list[str] = Field(default_factory=list)
    cookie_refresco_nombre: str = "sigat_refresco"
    cookie_segura: bool = True
    cookie_dominio: str | None = None

    # --- Proveedor institucional (RI-008)
    oidc_emisor: str | None = None
    oidc_cliente_id: str | None = None
    oidc_cliente_secreto: SecretStr | None = None

    # --- Almacenamiento de objetos
    s3_endpoint: str | None = None
    s3_region: str = "us-east-1"
    s3_bucket: str = "sigat-durazno-evidencia"
    s3_acceso: SecretStr = SecretStr("")
    s3_secreto: SecretStr = SecretStr("")
    s3_url_firmada_segundos: int = 600
    archivo_max_imagen_mb: int = 8
    archivo_max_documento_mb: int = 10

    # --- Cola de trabajo
    cola_esquema: str = "cola"
    cola_concurrencia: int = 2

    # --- Sincronización
    sync_max_operaciones_por_lote: int = 200
    sync_umbral_deriva_reloj_seg: int = 300

    # --- Correo
    smtp_host: str | None = None
    smtp_puerto: int = 587
    smtp_usuario: str | None = None
    smtp_clave: SecretStr | None = None
    smtp_remitente: str | None = None

    # --- Observabilidad
    log_nivel: str = "INFO"
    log_formato: Literal["json", "consola"] = "json"

    @model_validator(mode="after")
    def _exigencias_de_produccion(self) -> Self:
        """En producción no se arranca con valores inseguros."""
        if self.entorno == "produccion":
            secreto = self.jwt_secreto.get_secret_value()
            problemas = []
            if len(secreto) < 32 or secreto == "CAMBIAR":  # pragma: allowlist secret
                problemas.append("SIGAT_JWT_SECRETO debe tener al menos 32 caracteres")
            if not self.cookie_segura:
                problemas.append("SIGAT_COOKIE_SEGURA debe ser true")
            if self.depuracion:
                problemas.append("SIGAT_DEPURACION debe ser false")
            if problemas:
                raise ValueError("Configuración no apta para producción: " + "; ".join(problemas))
        return self


@lru_cache
def obtener_configuracion() -> Configuracion:
    return Configuracion()
