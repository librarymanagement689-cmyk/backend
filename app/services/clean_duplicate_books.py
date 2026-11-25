import asyncio
from collections import defaultdict

from app.database import (
    connect_to_mongo,
    close_mongo_connection,
    get_books_collection,
)


# ============================================================
# SAFETY SWITCH
# ============================================================

# FIRST RUN:
# True = preview only, NOTHING will be deleted.
#
# After confirming:
# False = actually delete the duplicates.
DRY_RUN = False


# ============================================================
# FIELDS USED TO IDENTIFY AN EXACT DUPLICATE
# ============================================================

DUPLICATE_FIELDS = [
    "serial_number",
    "title",
    "author",
    "author_alias",
    "price",
    "category",
    "language",
    "part_or_volume",
    "series_name",
    "volume_number",
    "total_volumes",
    "image_url",
]


async def cleanup_duplicates():

    await connect_to_mongo()

    books_col = get_books_collection()

    # ========================================================
    # GET ALL BOOKS
    # ========================================================

    books = await books_col.find({}).to_list(length=None)

    print()
    print("========================================")
    print("DUPLICATE BOOK CLEANUP")
    print("========================================")
    print(f"Total books in database: {len(books)}")
    print("========================================")

    # ========================================================
    # GROUP BY EXACT CATALOGUE DATA
    # ========================================================

    groups = defaultdict(list)

    for book in books:

        key = tuple(
            book.get(field)
            for field in DUPLICATE_FIELDS
        )

        groups[key].append(book)

    # ========================================================
    # FIND DUPLICATES
    # ========================================================

    duplicate_groups = [
        group
        for group in groups.values()
        if len(group) > 1
    ]

    records_to_delete = []

    for group in duplicate_groups:

        # Sort oldest → newest.
        # The oldest record is retained.
        group.sort(
            key=lambda x: x.get("created_at") or ""
        )

        keep = group[0]
        duplicates = group[1:]

        records_to_delete.extend(duplicates)

        # Show each duplicate group
        print()
        print(
            f"KEEP    : {keep.get('book_id')} | "
            f"{keep.get('title')} | "
            f"Serial: {keep.get('serial_number')}"
        )

        for duplicate in duplicates:

            print(
                f"DELETE  : {duplicate.get('book_id')} | "
                f"{duplicate.get('title')} | "
                f"Serial: {duplicate.get('serial_number')}"
            )

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("========================================")
    print("CLEANUP SUMMARY")
    print("========================================")
    print(f"Total database records : {len(books)}")
    print(f"Duplicate groups       : {len(duplicate_groups)}")
    print(f"Records to delete      : {len(records_to_delete)}")
    print(
        f"Records after cleanup  : "
        f"{len(books) - len(records_to_delete)}"
    )
    print("========================================")

    # ========================================================
    # SAFETY CHECK
    # ========================================================

    if DRY_RUN:

        print()
        print("DRY RUN = TRUE")
        print("NO BOOKS WERE DELETED.")

        if (
            len(duplicate_groups) == 789
            and len(records_to_delete) == 789
        ):

            print()
            print("✓ EXACTLY 789 DUPLICATES FOUND")
            print("✓ EXPECTED REMAINING BOOKS: 4739")
            print()
            print(
                "Change DRY_RUN = False and run the script "
                "again to delete them."
            )

        else:

            print()
            print("⚠ WARNING")
            print(
                "The duplicate count is not 789."
            )
            print(
                "DO NOT change DRY_RUN to False."
            )

        await close_mongo_connection()
        return

    # ========================================================
    # DELETE DUPLICATES
    # ========================================================

    ids_to_delete = [
        book["_id"]
        for book in records_to_delete
        if "_id" in book
    ]

    if not ids_to_delete:

        print()
        print("No duplicates found. Nothing deleted.")

        await close_mongo_connection()
        return

    result = await books_col.delete_many(
        {
            "_id": {
                "$in": ids_to_delete
            }
        }
    )

    # ========================================================
    # FINAL RESULT
    # ========================================================

    print()
    print("========================================")
    print("CLEANUP COMPLETE")
    print("========================================")
    print(f"Deleted records : {result.deleted_count}")
    print(f"Expected        : 789")
    print(
        f"Remaining       : "
        f"{len(books) - result.deleted_count}"
    )
    print("========================================")

    await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(cleanup_duplicates())