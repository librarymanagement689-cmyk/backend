from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from app.schemas.member import MemberCreate, MemberUpdate, MemberResponse, MemberPaginatedResponse, DepositRefundUpdate, PastBookItem
from app.services.member_service import MemberService
from app.auth.dependencies import get_current_admin

router = APIRouter(prefix="/api/admin/members", tags=["Members"])

@router.post("", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
async def create_member(
    data: MemberCreate,
    current_admin: dict = Depends(get_current_admin)
):
    return await MemberService.create_member(data)

@router.get("", response_model=MemberPaginatedResponse)
async def get_members(
    search: Optional[str] = Query(None, description="Search name, email, phone, or member_id"),
    status: Optional[str] = Query(None, description="active, inactive, or expired"),
    subscription_type_id: Optional[str] = Query(None, description="Filter by subscription type"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_admin: dict = Depends(get_current_admin)
):
    return await MemberService.get_members(
        search=search,
        status=status,
        subscription_type_id=subscription_type_id,
        page=page,
        limit=limit
    )

@router.get("/{member_id}", response_model=MemberResponse)
async def get_member(
    member_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    member = await MemberService.get_member_by_id(member_id)
    if not member:
        raise HTTPException(status_code=404, detail=f"Member {member_id} not found")
    return member

@router.put("/{member_id}", response_model=MemberResponse)
async def update_member(
    member_id: str,
    data: MemberUpdate,
    current_admin: dict = Depends(get_current_admin)
):
    return await MemberService.update_member(member_id, data)

@router.delete("/{member_id}")
async def delete_member(
    member_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    success = await MemberService.delete_member(member_id)
    return {"message": f"Member {member_id} deleted successfully", "success": success}

@router.get("/{member_id}/orders")
async def get_member_borrowing_history(
    member_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    return await MemberService.get_member_orders(member_id)

@router.patch("/{member_id}/deposit-refund", response_model=MemberResponse)
async def toggle_deposit_refund(
    member_id: str,
    data: DepositRefundUpdate,
    current_admin: dict = Depends(get_current_admin)
):
    return await MemberService.toggle_deposit_refund(member_id, data)

@router.get("/{member_id}/previously-borrowed-books")
async def get_member_previously_borrowed_books(
    member_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    return await MemberService.get_member_previously_borrowed_books(member_id)

@router.post("/{member_id}/past-books", response_model=MemberResponse)
async def add_past_book(
    member_id: str,
    item: PastBookItem,
    current_admin: dict = Depends(get_current_admin)
):
    return await MemberService.add_past_book(member_id, item)

@router.delete("/{member_id}/past-books/{book_id}", response_model=MemberResponse)
async def remove_past_book(
    member_id: str,
    book_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    return await MemberService.remove_past_book(member_id, book_id)
