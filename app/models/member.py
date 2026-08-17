from datetime import datetime, timezone
from typing import Optional, Literal
from pydantic import BaseModel, Field, EmailStr

class MemberModel(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    member_id: str  # e.g., MEM-00001
    name: str
    phone: str
    email: EmailStr
    subscription_type_id: str  # References subscription_id e.g. SUB-00001
    subscription_start_date: str  # Format: YYYY-MM-DD
    subscription_end_date: str    # Format: YYYY-MM-DD
    status: Literal["active", "inactive", "expired"] = "active"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }
