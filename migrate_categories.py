import asyncio

from app.database import (
    connect_to_mongo,
    close_mongo_connection,
    get_books_collection,
    get_categories_collection,
)
from app.utils.helpers import generate_unique_id, current_utc_datetime


async def migrate_categories():
    print("Starting category migration...")

    books_col = get_books_collection()
    categories_col = get_categories_collection()

    # Get all distinct, non-empty category names currently used by books
    categories = await books_col.distinct("category")

    categories = sorted(
        {
            str(category).strip()
            for category in categories
            if category and str(category).strip()
        },
        key=str.lower
    )

    print(f"Found {len(categories)} existing categories in books.")

    created = 0
    skipped = 0

    for category_name in categories:

        # Case-insensitive duplicate check
        existing = await categories_col.find_one({
            "name": {
                "$regex": f"^{category_name}$",
                "$options": "i"
            }
        })

        if existing:
            print(f"SKIPPED: {category_name}")
            skipped += 1
            continue

        category_id = await generate_unique_id(
            "category_id",
            "CAT",
            5
        )

        now = current_utc_datetime()

        category_doc = {
            "category_id": category_id,
            "name": category_name,
            "description": None,
            "is_active": True,
            "created_at": now,
            "updated_at": now
        }

        await categories_col.insert_one(category_doc)

        print(f"CREATED: {category_name} → {category_id}")
        created += 1

    print()
    print("========================================")
    print("CATEGORY MIGRATION COMPLETE")
    print("========================================")
    print(f"Categories found : {len(categories)}")
    print(f"Categories created: {created}")
    print(f"Categories skipped: {skipped}")
    print("========================================")


async def main():
    try:
        await connect_to_mongo()
        await migrate_categories()
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(main())