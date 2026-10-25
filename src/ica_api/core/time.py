"""Utilidades de tiempo.

El dominio guarda en UTC; la zona del predio se aplica al presentar (ADR-10).
"""

from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(tz=UTC)
