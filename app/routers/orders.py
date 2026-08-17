from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from app.schemas.order import (
    OrderCreate, OrderResponse, OrderPaginatedResponse, ReturnBooksRequest, SendRemindersResponse
)
from app.services.order_service import OrderService
from app.auth.dependencies import get_current_admin

router = APIRouter(prefix="/api/admin/orders", tags=["Orders"])

@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    data: OrderCreate,
    current_admin: dict = Depends(get_current_admin)
):
    """
    Creates a library lending order. Automatically validates member, verifies availability of selected books,
    fetches master prices from DB, snapshots title & price into order items, calculates subtotal,
    and updates book availability to borrowed.
    """
    return await OrderService.create_order(data)

@router.get("", response_model=OrderPaginatedResponse)
async def get_orders(
    search: Optional[str] = Query(None, description="Search order_id, member_id, book title, or book_id"),
    member_id: Optional[str] = Query(None, description="Filter by member ID"),
    status: Optional[str] = Query(None, description="active, returned, overdue, or cancelled"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_admin: dict = Depends(get_current_admin)
):
    return await OrderService.get_orders(
        search=search,
        member_id=member_id,
        status=status,
        page=page,
        limit=limit
    )

@router.post("/send-reminders", response_model=SendRemindersResponse)
async def send_due_date_reminders(
    current_admin: dict = Depends(get_current_admin)
):
    """
    Triggers due-date reminder emails for active/overdue orders approaching their due date.
    Prevents duplicate emails.
    """
    return await OrderService.send_due_date_reminders()

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    order = await OrderService.get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return order

@router.post("/{order_id}/return", response_model=OrderResponse)
async def return_books(
    order_id: str,
    request: ReturnBooksRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """
    Returns specified books (or all unreturned books if list is empty/None) in an order.
    Updates returned state, sets returned_date, and marks books back as available.
    """
    return await OrderService.return_books(order_id, request)
