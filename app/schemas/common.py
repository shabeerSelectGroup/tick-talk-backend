from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str


class Meta(BaseModel):
    page: int | None = None
    per_page: int | None = None
    total: int | None = None


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    error: ErrorDetail | None = None
    meta: Meta | None = None


def ok(data: Any, meta: Meta | None = None) -> dict:
    return {"success": True, "data": data, "error": None, "meta": meta}


def err(code: str, message: str) -> dict:
    return {"success": False, "data": None, "error": {"code": code, "message": message}, "meta": None}
