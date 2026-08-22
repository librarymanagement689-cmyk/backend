from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class OrderCreateItem(BaseModel):
    book_id: str = Field(..., min_length=1)
    lending_amount: float = Field(..., ge=0.0)


class OrderCreate(BaseModel):
    member_id: str = Field(..., min_length=1)
    items: List[OrderCreateItem] = Field(..., min_length=1)
    borrowed_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    due_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    amount_paid: float = Field(..., ge=0.0)


class OrderItemResponse(BaseModel):
    book_id: str
    title: str
    price: float
    lending_amount: float = 0.0
    returned: bool
    returned_date: Optional[str] = None


class OrderResponse(BaseModel):
    order_id: str
    member_id: str
    items: List[OrderItemResponse]
    borrowed_date: str
    due_date: str
    returned_date: Optional[str] = None
    subtotal: float
    amount_paid: float
    status: Literal["active", "returned", "overdue", "cancelled"]
    reminder_sent: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderPaginatedResponse(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: int
    items: List[OrderResponse]


class ReturnBooksRequest(BaseModel):
    book_ids: Optional[List[str]] = None


class SendRemindersResponse(BaseModel):
    sent_count: int
    message: str