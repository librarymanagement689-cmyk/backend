import asyncio
import logging
from datetime import date, timedelta
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings
from app.auth.security import hash_password
from app.utils.helpers import current_utc_datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed")

async def seed_database():
    logger.info(f"Connecting to database {settings.MONGODB_DATABASE} for seeding...")
    client = None
    try:
        client = AsyncIOMotorClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
        await client.admin.command('ping')
        logger.info("Successfully connected to live MongoDB Atlas cluster!")
    except Exception:
        try:
            client = AsyncIOMotorClient("mongodb://localhost:27017", serverSelectionTimeoutMS=1000)
            await client.admin.command('ping')
        except Exception:
            logger.warning("MongoDB host unreachable. Using in-memory mongomock database for seed demonstration...")
            import mongomock_motor
            client = mongomock_motor.AsyncMongoMockClient()

    db = client[settings.MONGODB_DATABASE]

    # Clear existing collections
    await db["admins"].delete_many({})
    await db["subscriptions"].delete_many({})
    await db["books"].delete_many({})
    await db["members"].delete_many({})
    await db["orders"].delete_many({})
    await db["counters"].delete_many({})

    now = current_utc_datetime()

    # 1. Seed Admin
    admin_doc = {
        "email": settings.ADMIN_EMAIL.lower().strip(),
        "name": "Head Librarian Admin",
        "hashed_password": hash_password(settings.ADMIN_INITIAL_PASSWORD),
        "created_at": now,
        "updated_at": now
    }
    await db["admins"].insert_one(admin_doc)
    logger.info(f"Seeded Admin: {settings.ADMIN_EMAIL}")

    # 2. Seed 3 Subscription Types
    subscriptions_data = [
        {
            "subscription_id": "SUB-00001",
            "name": "Standard Monthly",
            "description": "Borrow up to 3 books at a time for 30 days",
            "duration_days": 30,
            "price": 150.0,
            "is_active": True,
            "created_at": now,
            "updated_at": now
        },
        {
            "subscription_id": "SUB-00002",
            "name": "Quarterly Scholar",
            "description": "Borrow up to 5 books at a time for 90 days",
            "duration_days": 90,
            "price": 400.0,
            "is_active": True,
            "created_at": now,
            "updated_at": now
        },
        {
            "subscription_id": "SUB-00003",
            "name": "Annual Premium Pass",
            "description": "Unlimited borrowing access for 365 days",
            "duration_days": 365,
            "price": 1200.0,
            "is_active": True,
            "created_at": now,
            "updated_at": now
        }
    ]
    await db["subscriptions"].insert_many(subscriptions_data)
    await db["counters"].insert_one({"_id": "subscription_id", "seq": 3})
    logger.info("Seeded 3 Subscription Types.")

    # 3. Seed 20 Books (Tamil + English, Published + Unpublished, Available + Borrowed)
    books_data = [
        # Tamil Books
        {"book_id": "LIB-00001", "title": "தெய்வத்தின் குரல்", "author": "காஞ்சி பரமாச்சாரியார்", "price": 450.0, "category": "Philosophy", "language": "Tamil", "status": "available", "publish_on_website": True, "image_url": "https://example.com/deivathin_kural.jpg"},
        {"book_id": "LIB-00002", "title": "வேள்பாரி", "author": "சு. வெங்கடேசன்", "price": 600.0, "category": "Historical Fiction", "language": "Tamil", "status": "borrowed", "publish_on_website": True, "image_url": "https://example.com/velpari.jpg"},
        {"book_id": "LIB-00003", "title": "பொன்னியின் செல்வன்", "author": "கல்கி", "price": 850.0, "category": "Historical Fiction", "language": "Tamil", "status": "available", "publish_on_website": True, "image_url": "https://example.com/ps.jpg"},
        {"book_id": "LIB-00004", "title": "பார்த்திபன் கனவு", "author": "கல்கி", "price": 250.0, "category": "Historical Fiction", "language": "Tamil", "status": "available", "publish_on_website": False, "image_url": None},
        {"book_id": "LIB-00005", "title": "சிவகாமி யின் சபதம்", "author": "கல்கி", "price": 400.0, "category": "Historical Fiction", "language": "Tamil", "status": "borrowed", "publish_on_website": True, "image_url": None},
        {"book_id": "LIB-00006", "title": "பெண்மை என்பதை காப்பாற்ற வேண்டும்", "author": "அறிஞர் அண்ணா", "price": 200.0, "category": "Literature", "language": "Tamil", "status": "available", "publish_on_website": False, "image_url": None},
        {"book_id": "LIB-00007", "title": "திருக்குறள் நீதி உரை", "author": "திருவள்ளுவர்", "price": 300.0, "category": "Classics", "language": "Tamil", "status": "available", "publish_on_website": True, "image_url": None},
        {"book_id": "LIB-00008", "title": "கள்ளிக்காட்டு இதிகாசம்", "author": "வைரமுத்து", "price": 350.0, "category": "Novel", "language": "Tamil", "status": "available", "publish_on_website": True, "image_url": None},
        {"book_id": "LIB-00009", "title": "கருவாச்சி காவியம்", "author": "வைரமுத்து", "price": 280.0, "category": "Novel", "language": "Tamil", "status": "available", "publish_on_website": False, "image_url": None},
        {"book_id": "LIB-00010", "title": "ஒரு புளியமரத்தின் கதை", "author": "சுந்தர ராமசாமி", "price": 220.0, "category": "Fiction", "language": "Tamil", "status": "available", "publish_on_website": True, "image_url": None},

        # English Books
        {"book_id": "LIB-00011", "title": "The Alchemist", "author": "Paulo Coelho", "price": 250.0, "category": "Fiction", "language": "English", "status": "borrowed", "publish_on_website": True, "image_url": "https://example.com/alchemist.jpg"},
        {"book_id": "LIB-00012", "title": "Atomic Habits", "author": "James Clear", "price": 350.0, "category": "Self-Help", "language": "English", "status": "borrowed", "publish_on_website": True, "image_url": "https://example.com/atomic.jpg"},
        {"book_id": "LIB-00013", "title": "Ikigai", "author": "Héctor García", "price": 300.0, "category": "Self-Help", "language": "English", "status": "available", "publish_on_website": True, "image_url": None},
        {"book_id": "LIB-00014", "title": "Deep Work", "author": "Cal Newport", "price": 400.0, "category": "Productivity", "language": "English", "status": "available", "publish_on_website": False, "image_url": None},
        {"book_id": "LIB-00015", "title": "Clean Code", "author": "Robert C. Martin", "price": 750.0, "category": "Technology", "language": "English", "status": "available", "publish_on_website": True, "image_url": None},
        {"book_id": "LIB-00016", "title": "Design Patterns", "author": "Erich Gamma et al.", "price": 890.0, "category": "Technology", "language": "English", "status": "available", "publish_on_website": False, "image_url": None},
        {"book_id": "LIB-00017", "title": "To Kill a Mockingbird", "author": "Harper Lee", "price": 320.0, "category": "Classic", "language": "English", "status": "available", "publish_on_website": True, "image_url": None},
        {"book_id": "LIB-00018", "title": "1984", "author": "George Orwell", "price": 290.0, "category": "Dystopian", "language": "English", "status": "available", "publish_on_website": False, "image_url": None},
        {"book_id": "LIB-00019", "title": "Sapiens: A Brief History of Humankind", "author": "Yuval Noah Harari", "price": 500.0, "category": "History", "language": "English", "status": "borrowed", "publish_on_website": True, "image_url": None},
        {"book_id": "LIB-00020", "title": "Thinking, Fast and Slow", "author": "Daniel Kahneman", "price": 480.0, "category": "Psychology", "language": "English", "status": "available", "publish_on_website": True, "image_url": None}
    ]

    for b in books_data:
        b["created_at"] = now
        b["updated_at"] = now

    await db["books"].insert_many(books_data)
    await db["counters"].insert_one({"_id": "book_id", "seq": 20})
    logger.info("Seeded 20 Books (10 Tamil, 10 English).")

    # 4. Seed 5 Members
    today = date.today()
    members_data = [
        {
            "member_id": "MEM-00001",
            "name": "Ravi Kumar",
            "phone": "+91 98765 43210",
            "email": "ravi.kumar@example.com",
            "subscription_type_id": "SUB-00001",
            "subscription_start_date": (today - timedelta(days=15)).isoformat(),
            "subscription_end_date": (today + timedelta(days=15)).isoformat(),
            "status": "active",
            "created_at": now,
            "updated_at": now
        },
        {
            "member_id": "MEM-00002",
            "name": "Anitha Sundaram",
            "phone": "+91 98400 12345",
            "email": "anitha.sundaram@example.com",
            "subscription_type_id": "SUB-00002",
            "subscription_start_date": (today - timedelta(days=40)).isoformat(),
            "subscription_end_date": (today + timedelta(days=50)).isoformat(),
            "status": "active",
            "created_at": now,
            "updated_at": now
        },
        {
            "member_id": "MEM-00003",
            "name": "Karthik Raja",
            "phone": "+91 97100 99887",
            "email": "karthik.raja@example.com",
            "subscription_type_id": "SUB-00003",
            "subscription_start_date": (today - timedelta(days=100)).isoformat(),
            "subscription_end_date": (today + timedelta(days=265)).isoformat(),
            "status": "active",
            "created_at": now,
            "updated_at": now
        },
        {
            "member_id": "MEM-00004",
            "name": "Priya Dharshini",
            "phone": "+91 99440 55667",
            "email": "priya.dharshini@example.com",
            "subscription_type_id": "SUB-00001",
            "subscription_start_date": (today - timedelta(days=10)).isoformat(),
            "subscription_end_date": (today + timedelta(days=20)).isoformat(),
            "status": "active",
            "created_at": now,
            "updated_at": now
        },
        {
            "member_id": "MEM-00005",
            "name": "Vijay Raghavan",
            "phone": "+91 98840 11223",
            "email": "vijay.raghavan@example.com",
            "subscription_type_id": "SUB-00001",
            "subscription_start_date": (today - timedelta(days=60)).isoformat(),
            "subscription_end_date": (today - timedelta(days=30)).isoformat(),
            "status": "expired",
            "created_at": now,
            "updated_at": now
        }
    ]
    await db["members"].insert_many(members_data)
    await db["counters"].insert_one({"_id": "member_id", "seq": 5})
    logger.info("Seeded 5 Members.")

    # 5. Seed 5 Orders
    b_date1 = (today - timedelta(days=5)).isoformat()
    d_date1 = (today + timedelta(days=2)).isoformat()

    b_date2 = (today - timedelta(days=10)).isoformat()
    d_date2 = (today - timedelta(days=3)).isoformat()  # Overdue!

    b_date3 = (today - timedelta(days=20)).isoformat()
    d_date3 = (today - timedelta(days=13)).isoformat()
    r_date3 = (today - timedelta(days=14)).isoformat()  # Returned

    orders_data = [
        # Order 1: Active with 2 books for MEM-00001
        {
            "order_id": "ORD-00001",
            "member_id": "MEM-00001",
            "items": [
                {"book_id": "LIB-00011", "title": "The Alchemist", "price": 250.0, "returned": False, "returned_date": None},
                {"book_id": "LIB-00012", "title": "Atomic Habits", "price": 350.0, "returned": False, "returned_date": None}
            ],
            "borrowed_date": b_date1,
            "due_date": d_date1,
            "returned_date": None,
            "subtotal": 600.0,
            "amount_paid": 600.0,
            "status": "active",
            "reminder_sent": False,
            "reminder_sent_at": None,
            "created_at": now,
            "updated_at": now
        },
        # Order 2: Overdue order for MEM-00002 with Tamil book
        {
            "order_id": "ORD-00002",
            "member_id": "MEM-00002",
            "items": [
                {"book_id": "LIB-00002", "title": "வேள்பாரி", "price": 600.0, "returned": False, "returned_date": None}
            ],
            "borrowed_date": b_date2,
            "due_date": d_date2,
            "returned_date": None,
            "subtotal": 600.0,
            "amount_paid": 600.0,
            "status": "overdue",
            "reminder_sent": False,
            "reminder_sent_at": None,
            "created_at": now,
            "updated_at": now
        },
        # Order 3: Returned order for MEM-00003
        {
            "order_id": "ORD-00003",
            "member_id": "MEM-00003",
            "items": [
                {"book_id": "LIB-00007", "title": "திருக்குறள் நீதி உரை", "price": 300.0, "returned": True, "returned_date": r_date3}
            ],
            "borrowed_date": b_date3,
            "due_date": d_date3,
            "returned_date": r_date3,
            "subtotal": 300.0,
            "amount_paid": 300.0,
            "status": "returned",
            "reminder_sent": True,
            "reminder_sent_at": now,
            "created_at": now,
            "updated_at": now
        },
        # Order 4: Active order for MEM-00004 with Tamil & English book
        {
            "order_id": "ORD-00004",
            "member_id": "MEM-00004",
            "items": [
                {"book_id": "LIB-00005", "title": "சிவகாமி யின் சபதம்", "price": 400.0, "returned": False, "returned_date": None},
                {"book_id": "LIB-00019", "title": "Sapiens: A Brief History of Humankind", "price": 500.0, "returned": False, "returned_date": None}
            ],
            "borrowed_date": today.isoformat(),
            "due_date": (today + timedelta(days=7)).isoformat(),
            "returned_date": None,
            "subtotal": 900.0,
            "amount_paid": 900.0,
            "status": "active",
            "reminder_sent": False,
            "reminder_sent_at": None,
            "created_at": now,
            "updated_at": now
        },
        # Order 5: Today's order for MEM-00001
        {
            "order_id": "ORD-00005",
            "member_id": "MEM-00001",
            "items": [
                {"book_id": "LIB-00013", "title": "Ikigai", "price": 300.0, "returned": True, "returned_date": today.isoformat()}
            ],
            "borrowed_date": today.isoformat(),
            "due_date": (today + timedelta(days=7)).isoformat(),
            "returned_date": today.isoformat(),
            "subtotal": 300.0,
            "amount_paid": 300.0,
            "status": "returned",
            "reminder_sent": False,
            "reminder_sent_at": None,
            "created_at": now,
            "updated_at": now
        }
    ]

    await db["orders"].insert_many(orders_data)
    await db["counters"].insert_one({"_id": "order_id", "seq": 5})
    logger.info("Seeded 5 Orders.")

    client.close()
    logger.info("Database seeding completed successfully!")

if __name__ == "__main__":
    asyncio.run(seed_database())
