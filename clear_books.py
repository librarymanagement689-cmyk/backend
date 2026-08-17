import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("clear_books")

async def clear_books():
    logger.info(f"Connecting to MongoDB database '{settings.MONGODB_DATABASE}'...")
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DATABASE]

    # Delete all documents in books collection
    res = await db["books"].delete_many({})
    logger.info(f"Successfully deleted {res.deleted_count} books from database.")

    # Reset book_id counter in counters collection
    await db["counters"].delete_one({"_id": "book_id"})
    logger.info("Reset 'book_id' counter sequence.")

    client.close()

if __name__ == "__main__":
    asyncio.run(clear_books())
