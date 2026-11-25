import re
from datetime import datetime
from typing import List, Optional, Literal, Any
from pydantic import BaseModel, Field, EmailStr, field_validator

DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}")

def _normalize_date_input(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, str):
        v = v.strip()
        if not v or v.lower() in ("null", "undefined"):
            return None
        match = DATE_REGEX.match(v)
        if match:
            return match.group(0)
    return v

class PastBookItem(BaseModel):
    book_id: str
    title: Optional[str] = None
    date_borrowed: Optional[str] = None
    notes: Optional[str] = None

class MemberCreate(BaseModel):
    name: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=1)
    email: EmailStr
    subscription_type_id: str = Field(..., min_length=1)  # e.g., SUB-00001
    subscription_start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")  # YYYY-MM-DD
    subscription_end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")    # YYYY-MM-DD
    join_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    discontinued_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    security_deposit_amount: float = Field(default=0.0, ge=0.0)
    security_deposit_returned: bool = Field(default=False)
    security_deposit_returned_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    security_deposit_notes: Optional[str] = Field(default=None)
    past_books: Optional[List[PastBookItem]] = Field(default_factory=list)
    status: Literal["active", "inactive", "expired"] = "active"

    @field_validator(
        "subscription_start_date",
        "subscription_end_date",
        "join_date",
        "discontinued_date",
        "security_deposit_returned_date",
        mode="before"
    )
    @classmethod
    def clean_dates(cls, v: Any) -> Any:
        return _normalize_date_input(v)

class MemberUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    subscription_type_id: Optional[str] = None
    subscription_start_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    subscription_end_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    join_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    discontinued_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    security_deposit_amount: Optional[float] = Field(default=None, ge=0.0)
    security_deposit_returned: Optional[bool] = None
    security_deposit_returned_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    security_deposit_notes: Optional[str] = None
    past_books: Optional[List[PastBookItem]] = None
    status: Optional[Literal["active", "inactive", "expired"]] = None

    @field_validator(
        "subscription_start_date",
        "subscription_end_date",
        "join_date",
        "discontinued_date",
        "security_deposit_returned_date",
        mode="before"
    )
    @classmethod
    def clean_dates(cls, v: Any) -> Any:
        return _normalize_date_input(v)

class DepositRefundUpdate(BaseModel):
    security_deposit_returned: bool
    security_deposit_returned_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    security_deposit_notes: Optional[str] = None

    @field_validator("security_deposit_returned_date", mode="before")
    @classmethod
    def clean_dates(cls, v: Any) -> Any:
        return _normalize_date_input(v)

class MemberResponse(BaseModel):
    member_id: str
    name: str
    phone: str
    email: str
    subscription_type_id: str
    subscription_start_date: str
    subscription_end_date: str
    join_date: Optional[str] = None
    discontinued_date: Optional[str] = None
    security_deposit_amount: float = 0.0
    security_deposit_returned: bool = False
    security_deposit_returned_date: Optional[str] = None
    security_deposit_notes: Optional[str] = None
    past_books: List[PastBookItem] = Field(default_factory=list)
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class MemberPaginatedResponse(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: int
    items: List[MemberResponse]
