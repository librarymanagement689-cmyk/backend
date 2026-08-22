import re
from typing import Optional, Dict, Any

from fastapi import HTTPException, status

from app.database import get_categories_collection, get_books_collection
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.utils.helpers import generate_unique_id, current_utc_datetime


class CategoryService:

    @staticmethod
    async def create_category(data: CategoryCreate) -> dict:
        categories_col = get_categories_collection()

        name = data.name.strip()

        if not name:
            raise HTTPException(
                status_code=400,
                detail="Category name cannot be empty"
            )

        existing = await categories_col.find_one({
            "name": {
                "$regex": f"^{re.escape(name)}$",
                "$options": "i"
            }
        })

        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Category '{name}' already exists"
            )

        category_id = await generate_unique_id(
            "category_id",
            "CAT",
            5
        )

        now = current_utc_datetime()

        category_doc = {
            "category_id": category_id,
            "name": name,
            "description": data.description.strip()
            if data.description else None,
            "is_active": data.is_active,
            "created_at": now,
            "updated_at": now
        }

        await categories_col.insert_one(category_doc)

        return await CategoryService._with_book_count(category_doc)

    @staticmethod
    async def get_categories(
        active_only: bool = False
    ) -> Dict[str, Any]:

        categories_col = get_categories_collection()

        query = {}

        if active_only:
            query["is_active"] = True

        cursor = categories_col.find(query).sort("name", 1)

        categories = await cursor.to_list(length=1000)

        items = []

        for category in categories:
            items.append(
                await CategoryService._with_book_count(category)
            )

        return {
            "total": len(items),
            "items": items
        }

    @staticmethod
    async def get_category_by_id(
        category_id: str
    ) -> Optional[dict]:

        categories_col = get_categories_collection()

        category = await categories_col.find_one({
            "category_id": category_id
        })

        if not category:
            return None

        return await CategoryService._with_book_count(category)

    @staticmethod
    async def update_category(
        category_id: str,
        data: CategoryUpdate
    ) -> dict:

        categories_col = get_categories_collection()

        existing = await categories_col.find_one({
            "category_id": category_id
        })

        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Category {category_id} not found"
            )

        update_data = data.model_dump(exclude_unset=True)

        if "name" in update_data:
            name = update_data["name"].strip()

            if not name:
                raise HTTPException(
                    status_code=400,
                    detail="Category name cannot be empty"
                )

            duplicate = await categories_col.find_one({
                "name": {
                    "$regex": f"^{re.escape(name)}$",
                    "$options": "i"
                },
                "category_id": {
                    "$ne": category_id
                }
            })

            if duplicate:
                raise HTTPException(
                    status_code=409,
                    detail=f"Category '{name}' already exists"
                )

            update_data["name"] = name

        if "description" in update_data and update_data["description"]:
            update_data["description"] = (
                update_data["description"].strip()
            )

        if not update_data:
            return await CategoryService._with_book_count(existing)

        update_data["updated_at"] = current_utc_datetime()

        await categories_col.update_one(
            {"category_id": category_id},
            {"$set": update_data}
        )

        updated = await categories_col.find_one({
            "category_id": category_id
        })

        return await CategoryService._with_book_count(updated)

    @staticmethod
    async def delete_category(
        category_id: str
    ) -> dict:

        categories_col = get_categories_collection()
        books_col = get_books_collection()

        category = await categories_col.find_one({
            "category_id": category_id
        })

        if not category:
            raise HTTPException(
                status_code=404,
                detail=f"Category {category_id} not found"
            )

        book_count = await books_col.count_documents({
            "category": category["name"]
        })

        if book_count > 0:
            await categories_col.update_one(
                {"category_id": category_id},
                {
                    "$set": {
                        "is_active": False,
                        "updated_at": current_utc_datetime()
                    }
                }
            )

            return {
                "message": (
                    f"Category '{category['name']}' has "
                    f"{book_count} book(s). "
                    "It has been deactivated instead of deleted."
                ),
                "success": True,
                "deactivated": True
            }

        await categories_col.delete_one({
            "category_id": category_id
        })

        return {
            "message": f"Category '{category['name']}' deleted successfully",
            "success": True,
            "deactivated": False
        }

    @staticmethod
    async def _with_book_count(category: dict) -> dict:

        books_col = get_books_collection()

        book_count = await books_col.count_documents({
            "category": category.get("name")
        })

        return {
            "category_id": category.get("category_id"),
            "name": category.get("name"),
            "description": category.get("description"),
            "is_active": category.get("is_active", True),
            "book_count": book_count,
            "created_at": category.get("created_at"),
            "updated_at": category.get("updated_at")
        }