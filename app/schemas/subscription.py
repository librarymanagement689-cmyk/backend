from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class SubscriptionCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    duration_days: int = Field(..., gt=0)
    price: float = Field(..., ge=0.0)
    is_active: bool = True

class SubscriptionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    duration_days: Optional[int] = Field(default=None, gt=0)
    price: Optional[float] = Field(default=None, ge=0.0)
    is_active: Optional[bool] = None

class SubscriptionResponse(BaseModel):
    subscription_id: str
    name: str
    description: Optional[str] = None
    duration_days: int
    price: float
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
