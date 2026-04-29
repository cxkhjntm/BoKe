from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "ok"
    data: T | None = None


class PaginatedData(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    limit: int
