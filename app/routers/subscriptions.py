from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from app.schemas.subscription import SubscriptionCreate, SubscriptionUpdate, SubscriptionResponse
from app.services.subscription_service import SubscriptionService
from app.auth.dependencies import get_current_admin

router = APIRouter(prefix="/api/admin/subscriptions", tags=["Subscriptions"])

@router.post("", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    data: SubscriptionCreate,
    current_admin: dict = Depends(get_current_admin)
):
    return await SubscriptionService.create_subscription(data)

@router.get("", response_model=List[SubscriptionResponse])
async def get_subscriptions(
    active_only: bool = Query(False),
    current_admin: dict = Depends(get_current_admin)
):
    return await SubscriptionService.get_subscriptions(active_only=active_only)

@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    sub = await SubscriptionService.get_subscription_by_id(subscription_id)
    if not sub:
        raise HTTPException(status_code=404, detail=f"Subscription type {subscription_id} not found")
    return sub

@router.put("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: str,
    data: SubscriptionUpdate,
    current_admin: dict = Depends(get_current_admin)
):
    return await SubscriptionService.update_subscription(subscription_id, data)

@router.delete("/{subscription_id}")
async def delete_subscription(
    subscription_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    success = await SubscriptionService.delete_subscription(subscription_id)
    return {"message": f"Subscription {subscription_id} deleted successfully", "success": success}
