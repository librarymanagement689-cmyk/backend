from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, EmailStr

class MemberCreate(BaseModel):
    name: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=1)
    email: EmailStr
    subscription_type_id: str = Field(..., min_length=1)  # e.g., SUB-00001
    subscription_start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")  # YYYY-MM-DD
    subscription_end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")    # YYYY-MM-DD
    status: Literal["active", "inactive", "expired"] = "active"

class MemberUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    subscription_type_id: Optional[str] = None
    subscription_start_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    subscription_end_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    status: Optional[Literal["active", "inactive", "expired"]] = None

class MemberResponse(BaseModel):
    member_id: str
    name: str
    phone: str
    email: str
    subscription_type_id: str
    subscription_start_date: str
    subscription_end_date: str
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
