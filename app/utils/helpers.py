from typing import Optional
from datetime import datetime, timezone, date
from pymongo import ReturnDocument
from app.database import get_database

async def generate_unique_id(sequence_name: str, prefix: str, digits: int = 5) -> str:
    """
    Generates an atomic, sequential ID like LIB-00001, MEM-00001, ORD-00001, SUB-00001.
    Uses MongoDB counters collection find_one_and_update for thread/process safety.
    """
    db = get_database()
    counters = db["counters"]
    result = await counters.find_one_and_update(
        {"_id": sequence_name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    seq = result["seq"]
    return f"{prefix}-{str(seq).zfill(digits)}"

def current_utc_datetime() -> datetime:
    return datetime.now(timezone.utc)

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
