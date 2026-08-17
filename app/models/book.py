from datetime import datetime, timezone
from typing import Optional, Literal
from pydantic import BaseModel, Field

class BookModel(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    book_id: str  # e.g., LIB-00001
    title: str
    author: Optional[str] = None
    price: Optional[float] = Field(default=None, ge=0.0)
    category: Optional[str] = None
    language: Optional[str] = None  # English, Tamil, etc.
    part_or_volume: Optional[str] = None
    series_name: Optional[str] = None
    volume_number: Optional[str] = None
    total_volumes: Optional[str] = None
    status: Literal["available", "borrowed"] = "available"
    publish_on_website: bool = False
    image_url: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }

