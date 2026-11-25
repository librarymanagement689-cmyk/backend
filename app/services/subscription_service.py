from typing import Optional, List
from fastapi import HTTPException
from app.database import get_subscriptions_collection
from app.schemas.subscription import SubscriptionCreate, SubscriptionUpdate
from app.utils.helpers import generate_unique_id, current_utc_datetime, clean_doc, clean_docs

class SubscriptionService:
    @staticmethod
    async def create_subscription(data: SubscriptionCreate) -> dict:
        subs_col = get_subscriptions_collection()
        sub_id = await generate_unique_id("subscription_id", "SUB", 5)
        now = current_utc_datetime()
        sub_doc = {
            "subscription_id": sub_id,
            "name": data.name.strip(),
            "description": data.description.strip() if data.description else None,
            "duration_days": int(data.duration_days),
            "price": float(data.price),
            "is_active": data.is_active,
            "created_at": now,
            "updated_at": now
        }
        await subs_col.insert_one(sub_doc)
        return clean_doc(sub_doc)

    @staticmethod
    async def get_subscriptions(active_only: bool = False) -> List[dict]:
        subs_col = get_subscriptions_collection()
        query = {"is_active": True} if active_only else {}
        cursor = subs_col.find(query).sort("created_at", 1)
        items = await cursor.to_list(length=100)
        return clean_docs(items)

    @staticmethod
    async def get_subscription_by_id(subscription_id: str) -> Optional[dict]:
        subs_col = get_subscriptions_collection()
        doc = await subs_col.find_one({"subscription_id": subscription_id})
        return clean_doc(doc)

    @staticmethod
    async def update_subscription(subscription_id: str, data: SubscriptionUpdate) -> dict:
        subs_col = get_subscriptions_collection()
        existing = await subs_col.find_one({"subscription_id": subscription_id})
        if not existing:
            raise HTTPException(status_code=404, detail=f"Subscription type {subscription_id} not found")

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return clean_doc(existing)

        update_data["updated_at"] = current_utc_datetime()
        await subs_col.update_one({"subscription_id": subscription_id}, {"$set": update_data})
        updated = await subs_col.find_one({"subscription_id": subscription_id})
        return clean_doc(updated)

    @staticmethod
    async def delete_subscription(subscription_id: str) -> bool:
        subs_col = get_subscriptions_collection()
        existing = await subs_col.find_one({"subscription_id": subscription_id})
        if not existing:
            raise HTTPException(status_code=404, detail=f"Subscription type {subscription_id} not found")

        res = await subs_col.delete_one({"subscription_id": subscription_id})
        return res.deleted_count > 0
