"""Registro estructurado (structlog) con ``traza_id`` por petición.

Reglas (SEGURIDAD del móvil S-02/S-03 y Ley 1581 de 2012):
* Nunca registrar contraseñas, tokens, hashes de token ni el cuerpo de archivos.
* Datos personales (nombre, cédula, teléfono, correo) solo enmascarados.
* Coordenadas GPS de personas fuera del predio: no se registran (RNF-014).
"""

import logging

import structlog

from sigat_api.config import Configuracion


def configurar_logs(cfg: Configuracion) -> None:
    logging.basicConfig(level=cfg.log_nivel, format="%(message)s")
    renderer = (
        structlog.processors.JSONRenderer() if cfg.log_formato == "json" else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            renderer,
        ]
    )
