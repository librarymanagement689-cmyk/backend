import math
import re
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from fastapi import HTTPException, status
from app.database import get_books_collection, get_orders_collection, get_members_collection
from app.schemas.book import BookCreate, BookUpdate
from app.utils.helpers import generate_unique_id, current_utc_datetime

class BookService:
    @staticmethod
    async def create_book(data: BookCreate) -> dict:
        books_col = get_books_collection()
        book_id = await generate_unique_id("book_id", "LIB", 5)
        now = current_utc_datetime()
        book_doc = {
            "book_id": book_id,
            "serial_number": data.serial_number,
            "title": data.title.strip(),
            "author": data.author.strip() if data.author else None,
            "price": float(data.price) if data.price is not None else None,
            "category": data.category.strip() if data.category else None,
            "language": data.language.strip() if data.language else None,
            "part_or_volume": data.part_or_volume.strip() if data.part_or_volume else None,
            "series_name": data.series_name.strip() if data.series_name else None,
            "volume_number": str(data.volume_number).strip() if data.volume_number is not None else None,
            "total_volumes": str(data.total_volumes).strip() if data.total_volumes is not None else None,
            "status": "available",
            "publish_on_website": data.publish_on_website,
            "image_url": data.image_url,
            "created_at": now,
            "updated_at": now,
        }
        await books_col.insert_one(book_doc)
        return book_doc

    @staticmethod
    async def get_books(
        search: Optional[str] = None,
        serial_number: Optional[str] = None,
        author: Optional[str] = None,
        category: Optional[str] = None,
        language: Optional[str] = None,
        status: Optional[str] = None,
        publish_on_website: Optional[bool] = None,
        page: int = 1,
        limit: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        books_col = get_books_collection()
        query: Dict[str, Any] = {}

        if search and search.strip():
            search_term = re.escape(search.strip())
            regex = {"$regex": search_term, "$options": "i"}
            query["$or"] = [{"title": regex}, {"author_alias": regex}, {"author": regex}, {"series_name": regex}, {"book_id": regex}]

        if serial_number and serial_number.strip():
            query["serial_number"] = serial_number.strip()
        if author and author.strip():
            author_term = re.escape(author.strip())
            author_regex = {"$regex": author_term, "$options": "i"}

            query["$or"] = [
                {"author": author_regex},
                {"author_alias": author_regex}
    ]
        if category:
            query["category"] = category

        if language:
            query["language"] = language

        if status:
            query["status"] = status

        if publish_on_website is not None:
            query["publish_on_website"] = publish_on_website

        page = max(1, page)
        limit = min(max(1, limit), 100)
        skip = (page - 1) * limit

        sort_dir = -1 if sort_order.lower() == "desc" else 1
        total = await books_col.count_documents(query)
        cursor = books_col.find(query).sort(sort_by, sort_dir).skip(skip).limit(limit)
        items = await cursor.to_list(length=limit)

        total_pages = math.ceil(total / limit) if total > 0 else 1

        return {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "items": items
        }

    @staticmethod
    async def get_book_by_id(book_id: str) -> Optional[dict]:
        books_col = get_books_collection()
        return await books_col.find_one({"book_id": book_id})

    @staticmethod
    async def update_book(book_id: str, data: BookUpdate) -> dict:
        books_col = get_books_collection()
        existing = await books_col.find_one({"book_id": book_id})
        if not existing:
            raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return existing

        update_data["updated_at"] = current_utc_datetime()
        await books_col.update_one({"book_id": book_id}, {"$set": update_data})
        return await books_col.find_one({"book_id": book_id})

    @staticmethod
    async def delete_book(book_id: str) -> bool:
        books_col = get_books_collection()
        existing = await books_col.find_one({"book_id": book_id})
        if not existing:
            raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

        if existing.get("status") == "borrowed":
            raise HTTPException(status_code=400, detail=f"Cannot delete book {book_id} while it is currently borrowed")

        res = await books_col.delete_one({"book_id": book_id})
        return res.deleted_count > 0

    @staticmethod
    async def get_book_borrowing_history(book_id: str) -> dict:
        books_col = get_books_collection()
        book = await books_col.find_one({"book_id": book_id})
        if not book:
            raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

        orders_col = get_orders_collection()
        members_col = get_members_collection()

        cursor = orders_col.find({"items.book_id": book_id}).sort("created_at", -1)
        orders = await cursor.to_list(length=1000)

        history = []
        total_amount_collected = 0.0
        current_borrower = None

        for ord_doc in orders:
            # find item in order
            item = next((i for i in ord_doc.get("items", []) if i.get("book_id") == book_id), None)
            item_price = item.get("price", 0.0) if item else 0.0
            total_amount_collected += item_price

            member_id = ord_doc.get("member_id")
            member = await members_col.find_one({"member_id": member_id})
            member_name = member.get("name") if member else "Unknown"

            borrow_record = {
                "order_id": ord_doc.get("order_id"),
                "member_id": member_id,
                "member_name": member_name,
                "borrowed_date": ord_doc.get("borrowed_date"),
                "due_date": ord_doc.get("due_date"),
                "returned_date": ord_doc.get("returned_date") if item and item.get("returned") else None,
                "returned": item.get("returned", False) if item else False,
                "item_price": item_price
            }
            history.append(borrow_record)

            if ord_doc.get("status") in ["active", "overdue"] and item and not item.get("returned"):
                current_borrower = {
                    "member_id": member_id,
                    "member_name": member_name,
                    "borrowed_date": ord_doc.get("borrowed_date"),
                    "due_date": ord_doc.get("due_date")
                }

        return {
            "book": {
                "book_id": book.get("book_id"),
                "title": book.get("title"),
                "author": book.get("author"),
                "status": book.get("status"),
                "price": book.get("price")
            },
            "current_borrower": current_borrower,
            "times_borrowed": len(history),
            "total_amount_collected": total_amount_collected,
            "history": history
        }
