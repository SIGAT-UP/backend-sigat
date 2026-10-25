"""Unidad de trabajo.

Un caso de uso abre una unidad de trabajo, ejecuta cambios y confirma o
revierte todo junto (patrón Repository + Unit of Work).
"""

from types import TracebackType

from sqlalchemy.orm import Session

from ica_api.infra.db.session import get_session_factory


class UnitOfWork:
    def __init__(self) -> None:
        self.session: Session = get_session_factory()()

    def __enter__(self) -> "UnitOfWork":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            self.rollback()
        self.session.close()

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
