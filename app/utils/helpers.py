from typing import Optional
from datetime import datetime, timezone, date
from pymongo import ReturnDocument
from app.database import get_database

async def generate_unique_id(sequence_name: str, prefix: str, digits: int = 5) -> str:
    """
    Generates an atomic, sequential ID like LIB-00001, MEM-00001, ORD-00001, SUB-00001.
    Uses MongoDB counters collection find_one_and_update for thread/process safety.
    Guarantees uniqueness against existing collection documents.
    """
    db = get_database()
    counters = db["counters"]

    col_map = {
        "book_id": ("books", "book_id"),
        "member_id": ("members", "member_id"),
        "order_id": ("orders", "order_id"),
        "subscription_id": ("subscriptions", "subscription_id"),
    }

    while True:
        result = await counters.find_one_and_update(
            {"_id": sequence_name},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER
        )
        seq = result["seq"]
        generated_id = f"{prefix}-{str(seq).zfill(digits)}"

        if sequence_name in col_map:
            col_name, id_field = col_map[sequence_name]
            existing = await db[col_name].find_one({id_field: generated_id})
            if existing:
                continue

        return generated_id

def current_utc_datetime() -> datetime:
    return datetime.now(timezone.utc)

from typing import Any, Optional
from bson import ObjectId

def clean_doc(doc: Any) -> Any:
    if doc is None:
        return None
    if isinstance(doc, ObjectId):
        return str(doc)
    if isinstance(doc, dict):
        cleaned = {}
        for k, v in doc.items():
            if k == "_id":
                continue
            if isinstance(v, ObjectId):
                cleaned[k] = str(v)
            else:
                cleaned[k] = clean_doc(v)
        return cleaned
    if isinstance(doc, list):
        return [clean_doc(item) for item in doc]
    return doc

def clean_docs(docs: list) -> list:
    if not docs:
        return []
    return [clean_doc(d) for d in docs if d is not None]

def parse_date(val: Optional[str]) -> Optional[date]:
    if not val:
        return None
    if isinstance(val, date):
        return val
    try:
        return datetime.fromisoformat(str(val)).date()
    except ValueError:
        try:
            return datetime.strptime(str(val), "%Y-%m-%d").date()
        except ValueError:
            return None
