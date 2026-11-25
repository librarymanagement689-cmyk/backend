from datetime import datetime, date
from typing import Dict, Any, Optional
from app.database import (
    get_books_collection,
    get_members_collection,
    get_orders_collection,
)

from app.utils.helpers import clean_doc, clean_docs

class ReportService:
    @staticmethod
    async def get_dashboard_stats() -> Dict[str, Any]:
        books_col = get_books_collection()
        members_col = get_members_collection()
        orders_col = get_orders_collection()

        today_str = date.today().isoformat()
        current_month_prefix = date.today().strftime("%Y-%m")

        total_books = await books_col.count_documents({})
        available_books = await books_col.count_documents({"status": "available"})
        borrowed_books = await books_col.count_documents({"status": "borrowed"})
        published_books = await books_col.count_documents({"publish_on_website": True})
        unpublished_books = await books_col.count_documents({"publish_on_website": False})

        total_members = await members_col.count_documents({})

        # Dynamic overdue calculation
        active_orders = await orders_col.count_documents({"status": "active", "due_date": {"$gte": today_str}})
        overdue_orders = await orders_col.count_documents({
            "$or": [
                {"status": "overdue"},
                {"status": "active", "due_date": {"$lt": today_str}}
            ]
        })

        # Today's orders & collection (using borrowed_date or created_at)
        todays_orders_cursor = orders_col.find({"borrowed_date": today_str})
        todays_orders_list = await todays_orders_cursor.to_list(length=10000)
        todays_orders_count = len(todays_orders_list)
        todays_collection = sum(float(o.get("amount_paid", 0.0)) for o in todays_orders_list)

        # Monthly collection
        monthly_orders_cursor = orders_col.find({"borrowed_date": {"$regex": f"^{current_month_prefix}"}})
        monthly_orders_list = await monthly_orders_cursor.to_list(length=50000)
        monthly_collection = sum(float(o.get("amount_paid", 0.0)) for o in monthly_orders_list)

        return {
            "total_books": total_books,
            "available_books": available_books,
            "borrowed_books": borrowed_books,
            "published_books": published_books,
            "unpublished_books": unpublished_books,
            "total_members": total_members,
            "active_orders": active_orders,
            "overdue_orders": overdue_orders,
            "todays_orders": todays_orders_count,
            "todays_collection": round(todays_collection, 2),
            "monthly_collection": round(monthly_collection, 2)
        }

    @staticmethod
    async def get_daily_report(report_date: Optional[str] = None) -> Dict[str, Any]:
        orders_col = get_orders_collection()
        target_date = report_date if report_date else date.today().isoformat()

        cursor = orders_col.find({"borrowed_date": target_date})
        orders = await cursor.to_list(length=10000)

        total_orders = len(orders)
        collection = sum(float(o.get("amount_paid", 0.0)) for o in orders)

        return {
            "date": target_date,
            "total_orders": total_orders,
            "collection": round(collection, 2),
            "orders": clean_docs(orders)
        }

    @staticmethod
    async def get_monthly_report(year_month: Optional[str] = None) -> Dict[str, Any]:
        orders_col = get_orders_collection()
        target_month = year_month if year_month else date.today().strftime("%Y-%m")

        cursor = orders_col.find({"borrowed_date": {"$regex": f"^{target_month}"}})
        orders = await cursor.to_list(length=50000)

        total_orders = len(orders)
        collection = sum(float(o.get("amount_paid", 0.0)) for o in orders)

        return {
            "year_month": target_month,
            "total_orders": total_orders,
            "collection": round(collection, 2)
        }

    @staticmethod
    async def get_book_collection_report(book_id: str) -> Dict[str, Any]:
        orders_col = get_orders_collection()
        books_col = get_books_collection()

        book = await books_col.find_one({"book_id": book_id})
        book_title = book.get("title") if book else "Unknown"

        cursor = orders_col.find({"items.book_id": book_id})
        orders = await cursor.to_list(length=10000)

        times_borrowed = len(orders)
        total_amount_collected = 0.0

        for o in orders:
            for item in o.get("items", []):
                if item.get("book_id") == book_id:
                    total_amount_collected += float(item.get("price", 0.0))

        return {
            "book_id": book_id,
            "title": book_title,
            "times_borrowed": times_borrowed,
            "total_amount_collected": round(total_amount_collected, 2)
        }
