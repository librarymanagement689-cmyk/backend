"""
publish_existing_books.py
=========================
ONE-TIME MIGRATION: Set publish_on_website = True for all existing books in MongoDB.

SAFETY RULES:
  - Does NOT delete any book records
  - Does NOT modify titles, authors, prices, book_ids, or any other field
  - Only updates the publish_on_website boolean flag
  - Future CSV imports will still default to publish_on_website = False (unchanged)

Usage:
    cd backend
    python publish_existing_books.py
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load .env from same directory
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "library_db")


async def publish_all_existing_books():
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
    except ImportError:
        print("ERROR: motor not installed. Run: pip install motor")
        sys.exit(1)

    print(f"Connecting to MongoDB: {MONGODB_URI}")
    print(f"Database: {MONGODB_DATABASE}")

    client = AsyncIOMotorClient(MONGODB_URI, serverSelectionTimeoutMS=8000)

    try:
        await client.admin.command("ping")
        print("OK: Connected to MongoDB successfully.")
    except Exception as e:
        print(f"ERROR: Could not connect to MongoDB: {e}")
        print("Trying local fallback: mongodb://localhost:27017 ...")
        try:
            client = AsyncIOMotorClient("mongodb://localhost:27017", serverSelectionTimeoutMS=3000)
            await client.admin.command("ping")
            print("OK: Connected to local MongoDB.")
        except Exception as e2:
            print(f"ERROR: Local MongoDB also failed: {e2}")
            sys.exit(1)

    db = client[MONGODB_DATABASE]
    books_col = db["books"]

    # Count total books BEFORE migration
    total_books = await books_col.count_documents({})
    already_published = await books_col.count_documents({"publish_on_website": True})
    to_publish = await books_col.count_documents({"publish_on_website": False})

    print(f"\nBook counts before migration:")
    print(f"   Total books:          {total_books}")
    print(f"   Already published:    {already_published}")
    print(f"   To be published now:  {to_publish}")

    if to_publish == 0:
        print("\nOK: All books are already published. Nothing to update.")
        client.close()
        return

    print(f"\nProcessing: Setting publish_on_website = True for {to_publish} book(s)...")

    result = await books_col.update_many(
        {"publish_on_website": False},
        {"$set": {"publish_on_website": True}}
    )

    print(f"\nOK: Migration complete!")
    print(f"   Documents matched:  {result.matched_count}")
    print(f"   Documents modified: {result.modified_count}")

    # Verify
    published_after = await books_col.count_documents({"publish_on_website": True})
    unpublished_after = await books_col.count_documents({"publish_on_website": False})
    print(f"\nBook counts after migration:")
    print(f"   Published books:    {published_after}")
    print(f"   Unpublished books:  {unpublished_after}")
    print(f"\nDONE: All {published_after} books are now visible on the public website.")
    print("   Future CSV imports will still default to publish_on_website = False.")

    client.close()


if __name__ == "__main__":
    asyncio.run(publish_all_existing_books())
