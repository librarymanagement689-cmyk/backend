from datetime import datetime, timezone
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class OrderItem(BaseModel):
    book_id: str
    title: str
    price: float = Field(ge=0.0)
    returned: bool = False
    returned_date: Optional[str] = None  # Format: YYYY-MM-DD or ISO string

class OrderModel(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    order_id: str  # e.g., ORD-00001
    member_id: str  # e.g., MEM-00001
    items: List[OrderItem]
    borrowed_date: str  # Format: YYYY-MM-DD
    due_date: str       # Format: YYYY-MM-DD
    returned_date: Optional[str] = None
    total_mrp: float = Field(default=0.0, ge=0.0)
    rental_amount: float = Field(default=0.0, ge=0.0)
    subtotal: float = Field(ge=0.0)
    amount_paid: float = Field(ge=0.0)
    status: Literal["active", "returned", "overdue", "cancelled"] = "active"
    reminder_sent: bool = False
    reminder_sent_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }
