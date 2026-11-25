import math
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from fastapi import HTTPException
from app.database import get_members_collection, get_subscriptions_collection, get_orders_collection, get_books_collection
from app.schemas.member import MemberCreate, MemberUpdate, PastBookItem
from app.utils.helpers import generate_unique_id, current_utc_datetime, clean_doc, clean_docs

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
        join_date_val = data.join_date or data.subscription_start_date
        member_doc = {
            "member_id": member_id,
            "name": data.name.strip(),
            "phone": data.phone.strip(),
            "email": data.email.lower().strip(),
            "subscription_type_id": data.subscription_type_id,
            "subscription_start_date": data.subscription_start_date,
            "subscription_end_date": data.subscription_end_date,
            "join_date": join_date_val,
            "discontinued_date": data.discontinued_date,
            "security_deposit_amount": float(data.security_deposit_amount or 0.0),
            "security_deposit_returned": bool(data.security_deposit_returned),
            "security_deposit_returned_date": data.security_deposit_returned_date,
            "security_deposit_notes": data.security_deposit_notes.strip() if data.security_deposit_notes else None,
            "past_books": [b.model_dump() for b in data.past_books] if data.past_books else [],
            "status": data.status,
            "created_at": now,
            "updated_at": now
        }
        await members_col.insert_one(member_doc)
        return clean_doc(member_doc)

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
            "items": clean_docs(items)
        }

    @staticmethod
    async def get_member_by_id(member_id: str) -> Optional[dict]:
        members_col = get_members_collection()
        doc = await members_col.find_one({"member_id": member_id})
        return clean_doc(doc)

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
            return clean_doc(existing)

        update_data["updated_at"] = current_utc_datetime()
        await members_col.update_one({"member_id": member_id}, {"$set": update_data})
        updated = await members_col.find_one({"member_id": member_id})
        return clean_doc(updated)

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
        regex_query = {"$regex": f"^{member_id}$", "$options": "i"}
        cursor = orders_col.find({"$or": [{"member_id": member_id}, {"member_id": regex_query}]}).sort("created_at", -1)
        orders = await cursor.to_list(length=1000)

        subs_col = get_subscriptions_collection()
        sub = await subs_col.find_one({"subscription_id": member.get("subscription_type_id")})
        sub_name = sub.get("name") if sub else "Unknown"

        current_borrowed_books = []
        for ord_doc in orders:
            if not ord_doc.get("member_name"):
                ord_doc["member_name"] = member.get("name")
            if not ord_doc.get("subscription_name"):
                ord_doc["subscription_name"] = sub_name

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

        join_date_val = member.get("join_date") or member.get("subscription_start_date")
        
        # Calculate all unique previously borrowed book IDs (orders + manual past books)
        prev_book_ids = set()
        for ord_doc in orders:
            for itm in ord_doc.get("items", []):
                if itm.get("book_id"):
                    prev_book_ids.add(itm["book_id"])
        for pb in (member.get("past_books") or []):
            if isinstance(pb, dict) and pb.get("book_id"):
                prev_book_ids.add(pb["book_id"])
            elif isinstance(pb, str):
                prev_book_ids.add(pb)

        res = {
            "member": {
                "member_id": member.get("member_id"),
                "name": member.get("name"),
                "email": member.get("email"),
                "phone": member.get("phone"),
                "subscription_name": sub_name,
                "subscription_start_date": member.get("subscription_start_date"),
                "subscription_end_date": member.get("subscription_end_date"),
                "join_date": join_date_val,
                "discontinued_date": member.get("discontinued_date"),
                "security_deposit_amount": float(member.get("security_deposit_amount") or 0.0),
                "security_deposit_returned": bool(member.get("security_deposit_returned")),
                "security_deposit_returned_date": member.get("security_deposit_returned_date"),
                "security_deposit_notes": member.get("security_deposit_notes"),
                "past_books": member.get("past_books") or [],
                "status": member.get("status")
            },
            "current_borrowed_books": current_borrowed_books,
            "previously_borrowed_book_ids": list(prev_book_ids),
            "total_orders": len(orders),
            "orders": clean_docs(orders)
        }
        return clean_doc(res)

    @staticmethod
    async def add_past_book(member_id: str, item: PastBookItem) -> dict:
        members_col = get_members_collection()
        books_col = get_books_collection()
        existing = await members_col.find_one({"member_id": member_id})
        if not existing:
            raise HTTPException(status_code=404, detail=f"Member {member_id} not found")

        title = item.title
        if not title:
            b_doc = await books_col.find_one({"book_id": item.book_id})
            if b_doc:
                title = b_doc.get("title")
            else:
                title = item.book_id

        past_books = existing.get("past_books") or []
        for pb in past_books:
            if isinstance(pb, dict) and pb.get("book_id") == item.book_id:
                raise HTTPException(status_code=400, detail=f"Book {item.book_id} is already in member's past books record")

        new_item = {
            "book_id": item.book_id,
            "title": title,
            "date_borrowed": item.date_borrowed or date.today().isoformat(),
            "notes": item.notes.strip() if item.notes else None
        }
        past_books.append(new_item)
        now = current_utc_datetime()
        await members_col.update_one(
            {"member_id": member_id},
            {"$set": {"past_books": past_books, "updated_at": now}}
        )
        updated = await members_col.find_one({"member_id": member_id})
        return clean_doc(updated)

    @staticmethod
    async def remove_past_book(member_id: str, book_id: str) -> dict:
        members_col = get_members_collection()
        existing = await members_col.find_one({"member_id": member_id})
        if not existing:
            raise HTTPException(status_code=404, detail=f"Member {member_id} not found")

        past_books = existing.get("past_books") or []
        filtered = [pb for pb in past_books if (pb.get("book_id") != book_id if isinstance(pb, dict) else pb != book_id)]
        now = current_utc_datetime()
        await members_col.update_one(
            {"member_id": member_id},
            {"$set": {"past_books": filtered, "updated_at": now}}
        )
        updated = await members_col.find_one({"member_id": member_id})
        return clean_doc(updated)

    @staticmethod
    async def get_member_previously_borrowed_books(member_id: str) -> dict:
        members_col = get_members_collection()
        orders_col = get_orders_collection()
        existing = await members_col.find_one({"member_id": member_id})
        if not existing:
            raise HTTPException(status_code=404, detail=f"Member {member_id} not found")

        borrowed_map: Dict[str, dict] = {}
        for pb in (existing.get("past_books") or []):
            if isinstance(pb, dict) and pb.get("book_id"):
                bid = pb["book_id"]
                borrowed_map[bid] = {
                    "book_id": bid,
                    "title": pb.get("title") or bid,
                    "borrowed_date": pb.get("date_borrowed") or "Historical Record",
                    "source": "manual_record",
                    "notes": pb.get("notes")
                }
            elif isinstance(pb, str):
                borrowed_map[pb] = {
                    "book_id": pb,
                    "title": pb,
                    "borrowed_date": "Historical Record",
                    "source": "manual_record",
                    "notes": None
                }

        cursor = orders_col.find({"member_id": member_id})
        orders = await cursor.to_list(length=1000)
        for ord_doc in orders:
            for item in ord_doc.get("items", []):
                bid = item.get("book_id")
                if bid and bid not in borrowed_map:
                    borrowed_map[bid] = {
                        "book_id": bid,
                        "title": item.get("title") or bid,
                        "borrowed_date": ord_doc.get("borrowed_date"),
                        "due_date": ord_doc.get("due_date"),
                        "returned": item.get("returned", False),
                        "returned_date": item.get("returned_date"),
                        "order_id": ord_doc.get("order_id"),
                        "source": "order",
                        "notes": None
                    }

        all_items = list(borrowed_map.values())
        return {
            "member_id": member_id,
            "member_name": existing.get("name"),
            "total_borrowed_unique_books": len(all_items),
            "book_ids": list(borrowed_map.keys()),
            "items": all_items
        }

    @staticmethod
    async def toggle_deposit_refund(member_id: str, data: Any) -> dict:
        members_col = get_members_collection()
        existing = await members_col.find_one({"member_id": member_id})
        if not existing:
            raise HTTPException(status_code=404, detail=f"Member {member_id} not found")

        today_str = date.today().isoformat()
        now = current_utc_datetime()

        returned_val = bool(data.security_deposit_returned)
        returned_date_val = data.security_deposit_returned_date if returned_val else None
        if returned_val and not returned_date_val:
            returned_date_val = today_str

        update_fields = {
            "security_deposit_returned": returned_val,
            "security_deposit_returned_date": returned_date_val,
            "security_deposit_notes": data.security_deposit_notes.strip() if data.security_deposit_notes else None,
            "updated_at": now
        }

        await members_col.update_one({"member_id": member_id}, {"$set": update_fields})
        updated = await members_col.find_one({"member_id": member_id})
        return clean_doc(updated)
