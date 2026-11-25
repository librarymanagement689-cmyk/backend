import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings

logger = logging.getLogger("library_db")

class Database:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None

db_instance = Database()

async def connect_to_mongo():
    if db_instance.db is not None:
        logger.info("MongoDB connection already initialized.")
        return
    logger.info(f"Connecting to MongoDB at {settings.MONGODB_URI}...")
    try:
        client = AsyncIOMotorClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
        await client.admin.command('ping')
        db_instance.client = client
        db_instance.db = client[settings.MONGODB_DATABASE]
        logger.info(f"Successfully connected to MongoDB Atlas database: {settings.MONGODB_DATABASE}")
    except Exception as primary_err:
        logger.warning(f"Could not connect to configured MONGODB_URI ({primary_err}). Attempting local MongoDB mongodb://localhost:27017...")
        try:
            client = AsyncIOMotorClient("mongodb://localhost:27017", serverSelectionTimeoutMS=2000)
            await client.admin.command('ping')
            db_instance.client = client
            db_instance.db = client[settings.MONGODB_DATABASE]
            logger.info("Successfully connected to fallback local MongoDB database.")
        except Exception as local_err:
            logger.warning(f"Local MongoDB unavailable ({local_err}). Initializing in-memory MongoMock database engine for active execution...")
            import mongomock_motor
            client = mongomock_motor.AsyncMongoMockClient()
            db_instance.client = client
            db_instance.db = client[settings.MONGODB_DATABASE]
            logger.info("Operating with in-memory MongoMock database engine.")

    await create_indexes()


def get_categories_collection():
    return get_database()["categories"]

async def close_mongo_connection():
    if db_instance.client:
        db_instance.client.close()
        logger.info("MongoDB connection closed.")

async def create_indexes():
    if db_instance.db is None:
        return
    try:
        # Books Indexes
        books_col = db_instance.db["books"]
        await books_col.create_index("book_id", unique=True)
        await books_col.create_index("title")
        await books_col.create_index("author")
        await books_col.create_index("category")
        await books_col.create_index("language")
        await books_col.create_index("status")
        await books_col.create_index("publish_on_website")

        # Categories Indexes
        categories_col = db_instance.db["categories"]
        await categories_col.create_index("category_id", unique=True)
        await categories_col.create_index("name", unique=True)
        await categories_col.create_index("is_active")

        # Members Indexes
        members_col = db_instance.db["members"]
        await members_col.create_index("member_id", unique=True)
        await members_col.create_index("email", unique=True)
        await members_col.create_index("phone")
        await members_col.create_index("name")
        await members_col.create_index("status")

        # Subscriptions Indexes
        subs_col = db_instance.db["subscriptions"]
        await subs_col.create_index("subscription_id", unique=True)
        await subs_col.create_index("is_active")

        # Orders Indexes
        orders_col = db_instance.db["orders"]
        await orders_col.create_index("order_id", unique=True)
        await orders_col.create_index("member_id")
        await orders_col.create_index("due_date")
        await orders_col.create_index("status")
        await orders_col.create_index("borrowed_date")

        # Admins Indexes
        admins_col = db_instance.db["admins"]
        await admins_col.create_index("email", unique=True)

        logger.info("MongoDB indexes created successfully.")
    except Exception as e:
        logger.warning(f"Could not create MongoDB indexes (may be offline or read-only): {e}")

def get_database() -> AsyncIOMotorDatabase:
    if db_instance.db is None:
        raise RuntimeError("Database connection has not been initialized.")
    return db_instance.db

def get_admins_collection():
    return get_database()["admins"]

def get_books_collection():
    return get_database()["books"]

def get_members_collection():
    return get_database()["members"]

def get_subscriptions_collection():
    return get_database()["subscriptions"]

def get_orders_collection():
    return get_database()["orders"]
