from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException

from app.auth.dependencies import get_current_admin
from app.schemas.category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryListResponse
)
from app.services.category_service import CategoryService


# Public category routes
public_router = APIRouter(
    prefix="/api/categories",
    tags=["Categories"]
)


@public_router.get(
    "",
    response_model=CategoryListResponse
)
async def get_public_categories(
    active_only: bool = Query(True)
):
    return await CategoryService.get_categories(
        active_only=active_only
    )


# Admin category routes
admin_router = APIRouter(
    prefix="/api/admin/categories",
    tags=["Admin Categories"]
)


@admin_router.get(
    "",
    response_model=CategoryListResponse
)
async def get_admin_categories(
    active_only: bool = Query(False),
    current_admin: dict = Depends(get_current_admin)
):
    return await CategoryService.get_categories(
        active_only=active_only
    )


@admin_router.post(
    "",
    response_model=CategoryResponse,
    status_code=201
)
async def create_category(
    data: CategoryCreate,
    current_admin: dict = Depends(get_current_admin)
):
    return await CategoryService.create_category(data)


@admin_router.get(
    "/{category_id}",
    response_model=CategoryResponse
)
async def get_category(
    category_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    category = await CategoryService.get_category_by_id(
        category_id
    )

    if not category:
        raise HTTPException(
            status_code=404,
            detail=f"Category {category_id} not found"
        )

    return category


@admin_router.put(
    "/{category_id}",
    response_model=CategoryResponse
)
async def update_category(
    category_id: str,
    data: CategoryUpdate,
    current_admin: dict = Depends(get_current_admin)
):
    return await CategoryService.update_category(
        category_id,
        data
    )


@admin_router.delete(
    "/{category_id}"
)
async def delete_category(
    category_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    return await CategoryService.delete_category(
        category_id
    )