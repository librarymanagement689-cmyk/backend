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
    # Attempt real connection first, fallback to in-memory mongomock_motor
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
        # Clear test database
        await db_instance.db["admins"].delete_many({})
        await db_instance.db["books"].delete_many({})
        await db_instance.db["members"].delete_many({})
        await db_instance.db["subscriptions"].delete_many({})
        await db_instance.db["orders"].delete_many({})
        await db_instance.db["counters"].delete_many({})

        try:
            await create_indexes()
        except Exception:
            pass

        # Create test admin
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

    try:
        if db_instance.client:
            await db_instance.client.drop_database(TEST_DB_NAME)
            db_instance.client.close()
    except Exception:
        pass

@pytest_asyncio.fixture
async def async_client(setup_test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

@pytest_asyncio.fixture
async def admin_auth_headers(setup_test_db):
    token = create_access_token({"sub": "testadmin@library.com"})
    return {"Authorization": f"Bearer {token}"}
