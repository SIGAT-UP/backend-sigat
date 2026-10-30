"""Emisión y verificación de tokens.

* Token de ACCESO: JWT corto (``SIGAT_TOKEN_ACCESO_MINUTOS``). Reclamos:
  ``sub`` (usua_id), ``rol`` (rol_codigo), ``disp`` (disp_id), ``cli`` (web|movil),
  ``jti``, ``iat``, ``exp``, ``iss``, ``aud``.
* Token de REFRESCO: aleatorio y opaco (no JWT). Se guarda solo su SHA-256 en
  ``api.sesion_refresco`` (migración 0002) y ROTA en cada uso: si llega uno ya
  usado, se revoca toda la familia (detección de robo).
  - Web: cookie ``HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth``.
  - Móvil: en el cuerpo de la respuesta; la app lo guarda con flutter_secure_storage.
"""

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from sigat_api.compartido.errores import NoAutenticado
from sigat_api.compartido.tipos import Cliente, RolCodigo
from sigat_api.config import Configuracion

LONGITUD_MINIMA_SECRETO = 32


@dataclass(frozen=True, slots=True)
class ReclamosAcceso:
    usua_id: int
    rol: RolCodigo
    disp_id: UUID | None
    cliente: Cliente
    jti: str
    expira: datetime
    emitido: datetime


def hash_refresco(token: str) -> str:
    """SHA-256 en hexadecimal del token opaco (lo único que se guarda)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class ServicioTokens:
    def __init__(self, cfg: Configuracion) -> None:
        self._cfg = cfg

    def _secreto(self) -> str:
        secreto = self._cfg.jwt_secreto.get_secret_value()
        if len(secreto) < LONGITUD_MINIMA_SECRETO or secreto == "CAMBIAR":  # pragma: allowlist secret
            raise RuntimeError(
                "SIGAT_JWT_SECRETO no está configurado o es muy corto (mínimo 32 caracteres). "
                'Genere uno con: python -c "import secrets; print(secrets.token_urlsafe(64))"'
            )
        return secreto

    def emitir_acceso(
        self, usua_id: int, rol: RolCodigo, disp_id: UUID | None, cliente: Cliente
    ) -> tuple[str, int]:
        """Devuelve (jwt, segundos_de_vida)."""
        vida = self._cfg.token_acceso_minutos * 60
        ahora = datetime.now(UTC)
        reclamos = {
            "sub": str(usua_id),
            "rol": rol.value,
            "disp": str(disp_id) if disp_id else None,
            "cli": cliente.value,
            "jti": uuid.uuid4().hex,
            "iat": int(ahora.timestamp()),
            "exp": int((ahora + timedelta(seconds=vida)).timestamp()),
            "iss": self._cfg.jwt_emisor,
            "aud": self._cfg.jwt_audiencia,
        }
        token = jwt.encode(reclamos, self._secreto(), algorithm=self._cfg.jwt_algoritmo)
        return token, vida

    def verificar_acceso(self, token: str) -> ReclamosAcceso:
        """Valida firma, ``exp``, ``iss`` y ``aud``. Lanza ``NoAutenticado`` si algo falla."""
        try:
            datos = jwt.decode(
                token,
                self._secreto(),
                algorithms=[self._cfg.jwt_algoritmo],
                audience=self._cfg.jwt_audiencia,
                issuer=self._cfg.jwt_emisor,
                options={"require": ["sub", "exp", "iat", "iss", "aud", "jti"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise NoAutenticado("Su sesión venció. Inicie sesión de nuevo.", codigo="TOKEN_VENCIDO") from exc
        except jwt.PyJWTError as exc:
            raise NoAutenticado("El token de acceso no es válido.", codigo="TOKEN_INVALIDO") from exc
        try:
            return ReclamosAcceso(
                usua_id=int(datos["sub"]),
                rol=RolCodigo(datos["rol"]),
                disp_id=UUID(datos["disp"]) if datos.get("disp") else None,
                cliente=Cliente(datos["cli"]),
                jti=str(datos["jti"]),
                expira=datetime.fromtimestamp(int(datos["exp"]), UTC),
                emitido=datetime.fromtimestamp(int(datos["iat"]), UTC),
            )
        except (KeyError, ValueError) as exc:
            raise NoAutenticado("El token de acceso no es válido.", codigo="TOKEN_INVALIDO") from exc

    def nuevo_refresco(self) -> tuple[str, str]:
        """Devuelve (token_en_claro, sha256_hex). Solo el hash se persiste."""
        token = secrets.token_urlsafe(48)
        return token, hash_refresco(token)

    def vida_refresco(self, cliente: Cliente) -> timedelta:
        dias = (
            self._cfg.token_refresco_dias_web
            if cliente is Cliente.WEB
            else self._cfg.token_refresco_dias_movil
        )
        return timedelta(days=dias)
