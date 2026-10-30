"""Hash de contraseñas con argon2id (``usuario.usua_contrasena`` guarda SOLO el hash).

Política mínima sugerida (confirmar con el responsable de seguridad): 10+ caracteres,
no igual al usuario ni al correo, rechazo de contraseñas filtradas conocidas.
"""

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

_hasher = PasswordHasher()  # parámetros por defecto de argon2-cffi (argon2id)


def generar_hash(contrasena: str) -> str:
    return _hasher.hash(contrasena)


def verificar(contrasena: str, hash_guardado: str) -> bool:
    try:
        return _hasher.verify(hash_guardado, contrasena)
    except VerificationError:
        return False


def requiere_rehash(hash_guardado: str) -> bool:
    return _hasher.check_needs_rehash(hash_guardado)
