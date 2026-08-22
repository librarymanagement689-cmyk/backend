from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = True


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = None


class CategoryResponse(BaseModel):
    category_id: str
    name: str
    description: Optional[str] = None
    is_active: bool
    book_count: int = 0
    created_at: datetime
    updated_at: datetime


class CategoryListResponse(BaseModel):
    total: int
    items: list[CategoryResponse]