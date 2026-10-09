from typing import TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1, description="Page number starting at 1")
    limit: int = Field(20, ge=1, le=100, description="Items per page (max 100)")
    sort_by: str | None = Field(None, description="Field name to sort by")
    order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order: asc or desc")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


class PaginatedResponse[T](BaseModel):
    items: list[T]
    total: int = Field(..., description="Total count of records matching filter")
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Page size limit")
    pages: int = Field(..., description="Total number of pages")


class HealthCheckResponse(BaseModel):
    status: str = Field(..., json_schema_extra={"example": "ok"})
    environment: str
    database: str = Field(..., json_schema_extra={"example": "connected"})
    vector_store: str = Field(..., json_schema_extra={"example": "connected"})
    timestamp: str
