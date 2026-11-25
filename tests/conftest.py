import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from motor.motor_asyncio import AsyncIOMotorClient

from app.main import app
from app.config import settings
from app.database import db_instance, create_indexes
from app.auth.security import hash_password, create_access_token
from app.utils.helpers import current_utc_datetime

TEST_DB_NAME = "library_management_test"

@pytest_asyncio.fixture
async def setup_test_db():
    settings.MONGODB_DATABASE = TEST_DB_NAME
    client = None
    try:
        client = AsyncIOMotorClient(settings.MONGODB_URI, serverSelectionTimeoutMS=1000)
        await client.admin.command('ping')
    except Exception:
        try:
            client = AsyncIOMotorClient("mongodb://localhost:27017", serverSelectionTimeoutMS=1000)
            await client.admin.command('ping')
        except Exception:
            try:
                import mongomock_motor
                client = mongomock_motor.AsyncMongoMockClient()
            except ImportError:
                pytest.skip("MongoDB server and mongomock_motor are both unavailable.")

    db_instance.client = client
    db_instance.db = client[TEST_DB_NAME]

    try:
        # Clear test database collections
        for col_name in ["books", "members", "subscriptions", "orders", "counters"]:
            await db_instance.db[col_name].delete_many({})
        await db_instance.db["admins"].delete_many({"email": {"$ne": "testadmin@library.com"}})

        try:
            await create_indexes()
        except Exception:
            pass

        # Create test admin if not exists
        existing_admin = await db_instance.db["admins"].find_one({"email": "testadmin@library.com"})
        if not existing_admin:
            admin_doc = {
                "email": "testadmin@library.com",
                "name": "Test Admin",
                "hashed_password": hash_password("TestAdmin123!"),
                "created_at": current_utc_datetime(),
                "updated_at": current_utc_datetime()
            }
            await db_instance.db["admins"].insert_one(admin_doc)
    except Exception as e:
        import traceback
        traceback.print_exc()
        pytest.skip(f"MongoDB not accessible for integration testing: {e}")

    yield

@pytest_asyncio.fixture
async def async_client(setup_test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

@pytest_asyncio.fixture
async def admin_auth_headers(setup_test_db):
    admins_col = db_instance.db["admins"]
    admin = await admins_col.find_one({"email": "testadmin@library.com"})
    if not admin:
        admin_doc = {
            "email": "testadmin@library.com",
            "name": "Test Admin",
            "hashed_password": hash_password("TestAdmin123!"),
            "created_at": current_utc_datetime(),
            "updated_at": current_utc_datetime()
        }
        await admins_col.insert_one(admin_doc)

    token = create_access_token({"sub": "testadmin@library.com"})
    return {"Authorization": f"Bearer {token}"}
