"""Paginación común para las rutas de listado."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Query


@dataclass(frozen=True)
class Pagination:
    page: int = 1
    size: int = 25

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


def pagination_params(
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> Pagination:
    return Pagination(page=page, size=size)
