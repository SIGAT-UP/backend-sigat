"""Reloj del servidor. Inyectable para probar el modelo temporal (Arquitectura §4)."""

from datetime import UTC, datetime
from typing import Protocol


class Reloj(Protocol):
    def ahora(self) -> datetime: ...


class RelojSistema:
    def ahora(self) -> datetime:
        return datetime.now(UTC)
