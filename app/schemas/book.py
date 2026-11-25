from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class BookCreate(BaseModel):
    serial_number: Optional[str] = Field(default=None)
    title: str = Field(..., min_length=1)
    author: Optional[str] = None
    author_alias: Optional[str] = None
    price: Optional[float] = Field(default=None, ge=0.0)
    category: Optional[str] = None
    language: Optional[str] = None
    part_or_volume: Optional[str] = None
    series_name: Optional[str] = None
    volume_number: Optional[str] = None
    total_volumes: Optional[str] = None
    publish_on_website: bool = True
    image_url: Optional[str] = None

class BookUpdate(BaseModel):
    serial_number: Optional[str] = Field(default=None)
    title: Optional[str] = None
    author: Optional[str] = None
    author_alias: Optional[str] = None
    price: Optional[float] = Field(default=None, ge=0.0)
    category: Optional[str] = None
    language: Optional[str] = None
    part_or_volume: Optional[str] = None
    series_name: Optional[str] = None
    volume_number: Optional[str] = None
    total_volumes: Optional[str] = None
    status: Optional[Literal["available", "borrowed"]] = None
    publish_on_website: Optional[bool] = None
    image_url: Optional[str] = None

class BookResponse(BaseModel):
    book_id: str
    serial_number: Optional[str] = Field(default=None)
    title: str
    author: Optional[str] = None
    author_alias: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    language: Optional[str] = None
    part_or_volume: Optional[str] = None
    series_name: Optional[str] = None
    volume_number: Optional[str] = None
    total_volumes: Optional[str] = None
    status: str
    publish_on_website: bool
    image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class BookPaginatedResponse(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: int
    items: List[BookResponse]

class CSVRowError(BaseModel):
    row: int
    field: str
    message: str

class CSVImportSummaryResponse(BaseModel):
    total_rows: int
    imported: int
    failed: int
    errors: List[CSVRowError]
