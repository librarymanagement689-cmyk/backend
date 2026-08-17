import math
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from fastapi import HTTPException
from app.database import get_orders_collection, get_books_collection, get_members_collection
from app.schemas.order import OrderCreate, ReturnBooksRequest
from app.services.email_service import EmailService
from app.config import settings
from app.utils.helpers import generate_unique_id, current_utc_datetime, parse_date

class OrderService:
    @staticmethod
    async def create_order(data: OrderCreate) -> dict:
        members_col = get_members_collection()
        books_col = get_books_collection()
        orders_col = get_orders_collection()

        # 1. Verify Member
        member = await members_col.find_one({"member_id": data.member_id})
        if not member:
            raise HTTPException(status_code=404, detail=f"Member {data.member_id} not found")

        if member.get("status") != "active":
            raise HTTPException(status_code=400, detail=f"Member {data.member_id} does not have an active subscription (Status: {member.get('status')})")

        # Validate dates
        b_date = parse_date(data.borrowed_date)
        d_date = parse_date(data.due_date)
        if b_date and d_date and d_date < b_date:
            raise HTTPException(status_code=400, detail="Due date cannot be before borrowed date")

        # 2. Verify and Snapshot Books
        if not data.book_ids:
            raise HTTPException(status_code=400, detail="At least one book must be selected for an order")

        # Check duplicate book IDs in same order request
        if len(data.book_ids) != len(set(data.book_ids)):
            raise HTTPException(status_code=400, detail="Duplicate books detected in the order request")

        order_items = []
        subtotal = 0.0

        for book_id in data.book_ids:
            book = await books_col.find_one({"book_id": book_id})
            if not book:
                raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

            if book.get("status") != "available":
                raise HTTPException(
                    status_code=400,
                    detail=f"Book '{book.get('title')}' ({book_id}) is currently not available (Status: {book.get('status')})"
                )

            current_price = float(book.get("price", 0.0))
            subtotal += current_price

            # Snapshot title & price into order item
            order_items.append({
                "book_id": book.get("book_id"),
                "title": book.get("title"),
                "price": current_price,
                "returned": False,
                "returned_date": None
            })

        # 3. Generate unique order_id & create order
        order_id = await generate_unique_id("order_id", "ORD", 5)
        now = current_utc_datetime()

        # Initial status calculation
        today_str = date.today().isoformat()
        initial_status = "active"
        if data.due_date < today_str:
            initial_status = "overdue"

        order_doc = {
            "order_id": order_id,
            "member_id": data.member_id,
            "items": order_items,
            "borrowed_date": data.borrowed_date,
            "due_date": data.due_date,
            "returned_date": None,
            "subtotal": round(subtotal, 2),
            "amount_paid": float(data.amount_paid),
            "status": initial_status,
            "reminder_sent": False,
            "reminder_sent_at": None,
            "created_at": now,
            "updated_at": now
        }

        # Insert order
        await orders_col.insert_one(order_doc)

        # 4. Change book status from available -> borrowed
        await books_col.update_many(
            {"book_id": {"$in": data.book_ids}},
            {"$set": {"status": "borrowed", "updated_at": now}}
        )

        return order_doc

    @staticmethod
    async def get_orders(
        search: Optional[str] = None,
        member_id: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        orders_col = get_orders_collection()
        query: Dict[str, Any] = {}

        if member_id:
            query["member_id"] = member_id

        if status:
            query["status"] = status

        if search:
            regex = {"$regex": search, "$options": "i"}
            query["$or"] = [
                {"order_id": regex},
                {"member_id": regex},
                {"items.title": regex},
                {"items.book_id": regex}
            ]

        page = max(1, page)
        limit = min(max(1, limit), 100)
        skip = (page - 1) * limit

        total = await orders_col.count_documents(query)
        cursor = orders_col.find(query).sort("created_at", -1).skip(skip).limit(limit)
        items = await cursor.to_list(length=limit)

        today_str = date.today().isoformat()
        # Compute dynamic status for active orders past due date
        for item in items:
            if item.get("status") == "active" and item.get("due_date") < today_str:
                item["status"] = "overdue"

        total_pages = math.ceil(total / limit) if total > 0 else 1

        return {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "items": items
        }

    @staticmethod
    async def get_order_by_id(order_id: str) -> Optional[dict]:
        orders_col = get_orders_collection()
        order = await orders_col.find_one({"order_id": order_id})
        if order:
            today_str = date.today().isoformat()
            if order.get("status") == "active" and order.get("due_date") < today_str:
                order["status"] = "overdue"
        return order

    @staticmethod
    async def return_books(order_id: str, request: ReturnBooksRequest) -> dict:
        orders_col = get_orders_collection()
        books_col = get_books_collection()

        order = await orders_col.find_one({"order_id": order_id})
        if not order:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

        if order.get("status") == "returned":
            raise HTTPException(status_code=400, detail=f"Order {order_id} has already been fully returned")

        items = order.get("items", [])
        target_book_ids = request.book_ids

        # If target_book_ids is empty/None, return all unreturned items
        if not target_book_ids:
            target_book_ids = [item["book_id"] for item in items if not item.get("returned")]

        if not target_book_ids:
            raise HTTPException(status_code=400, detail="No unreturned books selected for return")

        today_str = date.today().isoformat()
        now = current_utc_datetime()
        returned_book_ids = []

        for item in items:
            if item["book_id"] in target_book_ids:
                if item.get("returned"):
                    continue  # Already returned
                item["returned"] = True
                item["returned_date"] = today_str
                returned_book_ids.append(item["book_id"])

        if not returned_book_ids:
            raise HTTPException(status_code=400, detail="Selected books have already been returned")

        # Update returned books status to available
        await books_col.update_many(
            {"book_id": {"$in": returned_book_ids}},
            {"$set": {"status": "available", "updated_at": now}}
        )

        # Check if all items in order are now returned
        all_returned = all(item.get("returned", False) for item in items)
        new_order_status = order.get("status")
        returned_date_val = order.get("returned_date")

        if all_returned:
            new_order_status = "returned"
            returned_date_val = today_str

        # Update order in DB
        await orders_col.update_one(
            {"order_id": order_id},
            {"$set": {
                "items": items,
                "status": new_order_status,
                "returned_date": returned_date_val,
                "updated_at": now
            }}
        )

        return await orders_col.find_one({"order_id": order_id})

    @staticmethod
    async def send_due_date_reminders() -> Dict[str, Any]:
        """
        Scans orders due within REMINDER_DAYS_BEFORE_DUE days and sends reminder emails.
        Prevents duplicate emails by updating reminder_sent status.
        """
        orders_col = get_orders_collection()
        members_col = get_members_collection()

        today = date.today()
        reminder_threshold = today + timedelta(days=settings.REMINDER_DAYS_BEFORE_DUE)
        threshold_str = reminder_threshold.isoformat()

        # Query active/overdue orders that haven't had reminders sent
        query = {
            "status": {"$in": ["active", "overdue"]},
            "due_date": {"$lte": threshold_str},
            "reminder_sent": False
        }

        cursor = orders_col.find(query)
        due_orders = await cursor.to_list(length=500)

        sent_count = 0
        now = current_utc_datetime()

        for order in due_orders:
            member = await members_col.find_one({"member_id": order["member_id"]})
            if not member or not member.get("email"):
                continue

            unreturned_titles = [i["title"] for i in order.get("items", []) if not i.get("returned")]
            if not unreturned_titles:
                continue

            success = EmailService.send_due_date_reminder(
                to_email=member["email"],
                member_name=member.get("name", "Member"),
                order_id=order["order_id"],
                book_titles=unreturned_titles,
                due_date=order.get("due_date")
            )

            if success:
                sent_count += 1
                await orders_col.update_one(
                    {"order_id": order["order_id"]},
                    {"$set": {"reminder_sent": True, "reminder_sent_at": now, "updated_at": now}}
                )

        return {
            "sent_count": sent_count,
            "message": f"Successfully processed reminders. Sent {sent_count} email notification(s)."
        }
