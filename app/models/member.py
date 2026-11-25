from datetime import datetime, timezone
from typing import Optional, Literal, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr

class PastBookItemModel(BaseModel):
    book_id: str
    title: Optional[str] = None
    date_borrowed: Optional[str] = None
    notes: Optional[str] = None

class MemberModel(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    member_id: str  # e.g., MEM-00001
    name: str
    phone: str
    email: EmailStr
    subscription_type_id: str  # References subscription_id e.g. SUB-00001
    subscription_start_date: str  # Format: YYYY-MM-DD
    subscription_end_date: str    # Format: YYYY-MM-DD
    join_date: Optional[str] = None
    discontinued_date: Optional[str] = None
    security_deposit_amount: float = 0.0
    security_deposit_returned: bool = False
    security_deposit_returned_date: Optional[str] = None
    security_deposit_notes: Optional[str] = None
    past_books: List[Dict[str, Any]] = Field(default_factory=list)
    status: Literal["active", "inactive", "expired"] = "active"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }
