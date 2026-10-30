"""Huella de contenido para la idempotencia (R-T4, RN-010).

Algoritmo (el MÓVIL debe implementar EXACTAMENTE el mismo):

    contenido = {
        "entidad": ..., "accion": ..., "registro_id": ..., "version": ...,
        "linaje": ..., "t_observacion": <ISO 8601 tal como se envía>,
        "datos": {...}
    }
    hash_contenido = sha256( JCS(contenido) ).hexdigest()   # JCS = RFC 8785

* NO entran: cliente_id, t_captura, deriva_reloj_seg, confirma_deriva_reloj
  (un reenvío con otra hora de captura sigue siendo el mismo contenido).
* Mismo (disp_id, cliente_id) + mismo hash  -> idempotente_repetida (recepcion_sync).
* Mismo (disp_id, cliente_id) + hash distinto -> conflicto_contenido (recepcion_sync), no se aplica.
"""

import hashlib
from typing import Any

import rfc8785


def calcular(contenido: dict[str, Any]) -> str:
    return hashlib.sha256(rfc8785.dumps(contenido)).hexdigest()


def contenido_canonico(op: Any) -> dict[str, Any]:
    """Arma el diccionario del docstring a partir de ``OperacionSync``."""
    return {
        "entidad": str(op.entidad),
        "accion": str(op.accion),
        "registro_id": str(op.registro_id),
        "version": op.version,
        "linaje": str(op.linaje) if op.linaje else None,
        "t_observacion": op.t_observacion.isoformat(),
        "datos": op.datos,
    }
