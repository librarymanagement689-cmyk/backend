import math
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from fastapi import HTTPException
from app.database import get_members_collection, get_subscriptions_collection, get_orders_collection
from app.schemas.member import MemberCreate, MemberUpdate
from app.utils.helpers import generate_unique_id, current_utc_datetime

class MemberService:
    @staticmethod
    async def create_member(data: MemberCreate) -> dict:
        members_col = get_members_collection()
        subs_col = get_subscriptions_collection()

        # Verify subscription type exists
        sub = await subs_col.find_one({"subscription_id": data.subscription_type_id})
        if not sub:
            raise HTTPException(status_code=400, detail=f"Subscription type {data.subscription_type_id} does not exist")

        # Check unique email
        existing_email = await members_col.find_one({"email": data.email.lower().strip()})
        if existing_email:
            raise HTTPException(status_code=400, detail=f"Member with email {data.email} already exists")

        member_id = await generate_unique_id("member_id", "MEM", 5)
        now = current_utc_datetime()
        member_doc = {
            "member_id": member_id,
            "name": data.name.strip(),
            "phone": data.phone.strip(),
            "email": data.email.lower().strip(),
            "subscription_type_id": data.subscription_type_id,
            "subscription_start_date": data.subscription_start_date,
            "subscription_end_date": data.subscription_end_date,
            "status": data.status,
            "created_at": now,
            "updated_at": now
        }
        await members_col.insert_one(member_doc)
        return member_doc

    @staticmethod
    async def get_members(
        search: Optional[str] = None,
        status: Optional[str] = None,
        subscription_type_id: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        members_col = get_members_collection()
        query: Dict[str, Any] = {}

        if search:
            regex = {"$regex": search, "$options": "i"}
            query["$or"] = [{"name": regex}, {"email": regex}, {"phone": regex}, {"member_id": regex}]

        if status:
            query["status"] = status

        if subscription_type_id:
            query["subscription_type_id"] = subscription_type_id

        page = max(1, page)
        limit = min(max(1, limit), 100)
        skip = (page - 1) * limit

        total = await members_col.count_documents(query)
        cursor = members_col.find(query).sort("created_at", -1).skip(skip).limit(limit)
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
    async def get_member_by_id(member_id: str) -> Optional[dict]:
        members_col = get_members_collection()
        return await members_col.find_one({"member_id": member_id})

    @staticmethod
    async def update_member(member_id: str, data: MemberUpdate) -> dict:
        members_col = get_members_collection()
        existing = await members_col.find_one({"member_id": member_id})
        if not existing:
            raise HTTPException(status_code=404, detail=f"Member {member_id} not found")

        update_data = data.model_dump(exclude_unset=True)

        if "email" in update_data and update_data["email"]:
            new_email = update_data["email"].lower().strip()
            existing_email = await members_col.find_one({"email": new_email, "member_id": {"$ne": member_id}})
            if existing_email:
                raise HTTPException(status_code=400, detail=f"Email {new_email} is already in use by another member")
            update_data["email"] = new_email

        if "subscription_type_id" in update_data and update_data["subscription_type_id"]:
            subs_col = get_subscriptions_collection()
            sub = await subs_col.find_one({"subscription_id": update_data["subscription_type_id"]})
            if not sub:
                raise HTTPException(status_code=400, detail=f"Subscription type {update_data['subscription_type_id']} does not exist")

        if not update_data:
            return existing

        update_data["updated_at"] = current_utc_datetime()
        await members_col.update_one({"member_id": member_id}, {"$set": update_data})
        return await members_col.find_one({"member_id": member_id})

    @staticmethod
    async def delete_member(member_id: str) -> bool:
        members_col = get_members_collection()
        existing = await members_col.find_one({"member_id": member_id})
        if not existing:
            raise HTTPException(status_code=404, detail=f"Member {member_id} not found")

        orders_col = get_orders_collection()
        active_orders = await orders_col.count_documents({"member_id": member_id, "status": {"$in": ["active", "overdue"]}})
        if active_orders > 0:
            raise HTTPException(status_code=400, detail=f"Cannot delete member {member_id} with active/overdue borrowing orders")

        res = await members_col.delete_one({"member_id": member_id})
        return res.deleted_count > 0

    @staticmethod
    async def get_member_orders(member_id: str) -> dict:
        members_col = get_members_collection()
        member = await members_col.find_one({"member_id": member_id})
        if not member:
            raise HTTPException(status_code=404, detail=f"Member {member_id} not found")

        orders_col = get_orders_collection()
        cursor = orders_col.find({"member_id": member_id}).sort("created_at", -1)
        orders = await cursor.to_list(length=1000)

        subs_col = get_subscriptions_collection()
        sub = await subs_col.find_one({"subscription_id": member.get("subscription_type_id")})
        sub_name = sub.get("name") if sub else "Unknown"

        current_borrowed_books = []
        for ord_doc in orders:
            if ord_doc.get("status") in ["active", "overdue"]:
                for item in ord_doc.get("items", []):
                    if not item.get("returned"):
                        current_borrowed_books.append({
                            "order_id": ord_doc.get("order_id"),
                            "book_id": item.get("book_id"),
                            "title": item.get("title"),
                            "borrowed_date": ord_doc.get("borrowed_date"),
                            "due_date": ord_doc.get("due_date")
                        })

        return {
            "member": {
                "member_id": member.get("member_id"),
                "name": member.get("name"),
                "email": member.get("email"),
                "phone": member.get("phone"),
                "subscription_name": sub_name,
                "subscription_start_date": member.get("subscription_start_date"),
                "subscription_end_date": member.get("subscription_end_date"),
                "status": member.get("status")
            },
            "current_borrowed_books": current_borrowed_books,
            "total_orders": len(orders),
            "orders": orders
        }
