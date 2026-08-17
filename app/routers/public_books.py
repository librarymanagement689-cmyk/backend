import re
from typing import Optional, List, Any, Dict

from fastapi import APIRouter, Query, HTTPException

from app.schemas.book import BookResponse, BookPaginatedResponse
from app.services.book_service import BookService
from app.database import get_books_collection


router = APIRouter(
    prefix="/api/books",
    tags=["Public Books"]
)


# ============================================================
# PUBLIC INDIVIDUAL BOOK ENDPOINT
# ============================================================

@router.get(
    "",
    response_model=BookPaginatedResponse
)
async def get_public_books(
    search: Optional[str] = Query(
        None,
        description="Search title or author"
    ),
    category: Optional[str] = Query(
        None,
        description="Filter by category"
    ),
    language: Optional[str] = Query(
        None,
        description="Filter by language"
    ),
    page: int = Query(
        1,
        ge=1
    ),
    limit: int = Query(
        20,
        ge=1,
        le=100
    )
):
    """
    Public catalog endpoint returning ONLY published books.

    This endpoint is retained for compatibility with the existing
    application.

    It does NOT expose:
    - member information
    - borrowing history
    - internal admin information
    """

    return await BookService.get_books(
        search=search,
        category=category,
        language=language,
        status=None,
        publish_on_website=True,
        page=page,
        limit=limit
    )


# ============================================================
# PUBLIC GROUPED CATALOG
# ============================================================

@router.get(
    "/catalog",
    summary="Public catalog with multi-part books grouped"
)
async def get_public_catalog(
    search: Optional[str] = Query(
        None,
        description="Search title, author or series"
    ),
    category: Optional[str] = Query(
        None,
        description="Filter by category"
    ),
    language: Optional[str] = Query(
        None,
        description="Filter by language"
    ),
    page: int = Query(
        1,
        ge=1
    ),
    limit: int = Query(
        100,
        ge=1,
        le=200
    )
):
    """
    Public website catalog.

    IMPORTANT:

    The database keeps every physical book as an individual record.

    Example:

        LIB-00001 → Diary of a Wimpy Kid → Part 1
        LIB-00002 → Diary of a Wimpy Kid → Part 2
        ...
        LIB-00017 → Diary of a Wimpy Kid → Part 17

    Admin continues to see all 17 records individually.

    The public website, however, displays:

        Diary of a Wimpy Kid
        17 Parts

    as ONE catalog card.

    Individual parts are intentionally NOT exposed in the public
    catalog response.

    Standalone books remain individual catalog cards.
    """

    books_col = get_books_collection()

    # ========================================================
    # BUILD MONGODB QUERY
    # ========================================================

    query: Dict[str, Any] = {
        "publish_on_website": True
    }

    # --------------------------------------------------------
    # Search
    # --------------------------------------------------------

    if search and search.strip():

        search_term = re.escape(search.strip())

        regex = {
            "$regex": search_term,
            "$options": "i"
        }

        query["$or"] = [
            {"title": regex},
            {"author": regex},
            {"series_name": regex}
        ]

    # --------------------------------------------------------
    # Category
    # --------------------------------------------------------

    if category and category.strip():
        query["category"] = category.strip()

    # --------------------------------------------------------
    # Language
    # --------------------------------------------------------

    if language and language.strip():
        query["language"] = language.strip()

    # ========================================================
    # FETCH BOOKS
    # ========================================================

    cursor = books_col.find(query).sort(
        [
            ("series_name", 1),
            ("title", 1),
            ("volume_number", 1)
        ]
    )

    all_books = await cursor.to_list(
        length=limit
    )

    # ========================================================
    # IDENTIFY MULTI-PART TITLES
    # ========================================================
    #
    # We must NOT group ordinary duplicate books.
    #
    # Example:
    #
    # The Alchemist
    # The Alchemist
    #
    # These are NOT automatically a series.
    #
    # But:
    #
    # Diary of a Wimpy Kid - Part 1
    # Diary of a Wimpy Kid - Part 2
    #
    # should become ONE public collection.
    #
    # ========================================================

    title_part_counts: Dict[str, int] = {}

    for book in all_books:

        title = (
            book.get("title") or ""
        ).strip()

        part = (
            book.get("part_or_volume") or ""
        ).strip()

        series_name = (
            book.get("series_name") or ""
        ).strip()

        if not title:
            continue

        # Explicit series name
        if series_name:

            key = series_name

            title_part_counts[key] = (
                title_part_counts.get(key, 0) + 1
            )

        # Part/volume without series name
        elif part:

            key = title

            title_part_counts[key] = (
                title_part_counts.get(key, 0) + 1
            )

    # ========================================================
    # GROUP BOOKS
    # ========================================================

    series_map: Dict[
        str,
        List[Dict[str, Any]]
    ] = {}

    standalone: List[
        Dict[str, Any]
    ] = []

    for book in all_books:

        title = (
            book.get("title") or ""
        ).strip()

        part = (
            book.get("part_or_volume") or ""
        ).strip()

        explicit_series = (
            book.get("series_name") or ""
        ).strip()

        # ----------------------------------------------------
        # Explicit series_name has highest priority
        # ----------------------------------------------------

        if explicit_series:

            group_name = explicit_series

        # ----------------------------------------------------
        # Otherwise group only when multiple records for the
        # same title contain part/volume information.
        # ----------------------------------------------------

        elif (
            part
            and title_part_counts.get(title, 0) > 1
        ):

            group_name = title

        else:

            group_name = ""

        # ----------------------------------------------------
        # Add to collection
        # ----------------------------------------------------

        if group_name:

            if group_name not in series_map:
                series_map[group_name] = []

            series_map[group_name].append(book)

        # ----------------------------------------------------
        # Standalone
        # ----------------------------------------------------

        else:

            standalone.append(book)

    # ========================================================
    # SORT COLLECTION VOLUMES INTERNALLY
    # ========================================================
    #
    # This is only used internally to identify the collection.
    # The volumes themselves are NOT returned to the public API.
    #
    # Supports:
    #
    # Part 1
    # Part 2
    # Part 10
    # பகுதி 1
    # பகுதி 2
    #
    # ========================================================

    def get_volume_number(
        book: Dict[str, Any]
    ) -> int:

        volume_number = book.get(
            "volume_number"
        )

        if volume_number is not None:

            try:
                return int(volume_number)

            except (
                ValueError,
                TypeError
            ):
                pass

        part = str(
            book.get("part_or_volume") or ""
        )

        match = re.search(
            r"(\d+)",
            part
        )

        if match:
            return int(
                match.group(1)
            )

        return 999999

    for series_name in series_map:

        series_map[series_name].sort(
            key=lambda book: (
                get_volume_number(book),
                (
                    book.get("title") or ""
                ).strip().lower()
            )
        )

    # ========================================================
    # BUILD PUBLIC CATALOG
    # ========================================================

    catalog: List[
        Dict[str, Any]
    ] = []

    # ========================================================
    # MULTI-PART COLLECTIONS
    # ========================================================

    for series_name, volumes in series_map.items():

        if not volumes:
            continue

        first = volumes[0]

        # ----------------------------------------------------
        # Select the first available image from any volume.
        # ----------------------------------------------------

        collection_image = next(
            (
                volume.get("image_url")
                for volume in volumes
                if volume.get("image_url")
            ),
            None
        )

        # ----------------------------------------------------
        # Author
        # ----------------------------------------------------

        collection_author = next(
            (
                volume.get("author")
                for volume in volumes
                if volume.get("author")
            ),
            None
        )

        # ----------------------------------------------------
        # Collection-level public item
        #
        # IMPORTANT:
        # Individual volumes are NOT returned.
        # ----------------------------------------------------

        catalog.append(
            {
                "type": "series",

                "series_name": series_name,

                "total_volumes": len(
                    volumes
                ),

                "available_count": len(
                    volumes
                ),

                "borrowed_count": 0,

                "category": first.get(
                    "category"
                ),

                "language": first.get(
                    "language"
                ),

                "author": collection_author,

                "image_url": collection_image,

                "availability_message": (
                    "All parts available, "
                    "for availability and lending "
                    "details, please contact us directly."
                )
            }
        )

    # ========================================================
    # STANDALONE BOOKS
    # ========================================================

    for book in standalone:

        catalog.append(
            {
                "type": "book",

                "book_id": book.get(
                    "book_id"
                ),

                "title": book.get(
                    "title"
                ),

                "author": book.get(
                    "author"
                ),

                "category": book.get(
                    "category"
                ),

                "language": book.get(
                    "language"
                ),

                "status": book.get(
                    "status",
                    "available"
                ),

                "available": (
                    book.get("status")
                    == "available"
                ),

                "image_url": book.get(
                    "image_url"
                ),

                "price": book.get(
                    "price"
                ),

                "part_or_volume": book.get(
                    "part_or_volume"
                )
            }
        )

    # ========================================================
    # SEARCH RESULT TOTAL
    # ========================================================

    return {
        "total": len(catalog),

        "series_count": len(
            series_map
        ),

        "standalone_count": len(
            standalone
        ),

        "items": catalog
    }


# ============================================================
# PUBLIC INDIVIDUAL BOOK
# ============================================================

@router.get(
    "/{book_id}",
    response_model=BookResponse
)
async def get_public_book_by_id(
    book_id: str
):
    """
    Return an individual published book.

    This remains available for standalone books.

    Multi-part collections are represented as a single
    collection on the public catalog.
    """

    book = await BookService.get_book_by_id(
        book_id
    )

    if (
        not book
        or not book.get(
            "publish_on_website"
        )
    ):
        raise HTTPException(
            status_code=404,
            detail="Book not found"
        )

    return book