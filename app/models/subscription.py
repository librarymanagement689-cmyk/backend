from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field

class SubscriptionModel(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    subscription_id: str  # e.g., SUB-00001
    name: str
    description: Optional[str] = None
    duration_days: int = Field(gt=0, description="Duration in days, e.g., 30, 90, 365")
    price: float = Field(ge=0.0)
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }
