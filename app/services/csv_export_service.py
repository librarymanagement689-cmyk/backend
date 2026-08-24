import csv
import io
from typing import List, Dict, Any, Optional

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from app.database import get_books_collection


class CSVExportService:

    # These are the only fields the admin is allowed to export.
    AVAILABLE_FIELDS = {
        "book_id": "Book ID",
        "serial_number": "Serial Number",
        "title": "Book Name",
        "author": "Author",
        "author_alias": "Author Alias",
        "price": "Price",
        "category": "Category",
        "language": "Language",
        "part_or_volume": "Part / Volume",
        "series_name": "Series Name",
        "volume_number": "Volume Number",
        "total_volumes": "Total Volumes",
        "status": "Status",
        "publish_on_website": "Publish on Website",
        "image_url": "Image URL",
        "created_at": "Created At",
        "updated_at": "Updated At",
    }

    @staticmethod
    async def export_books_csv(
        fields: Optional[List[str]] = None,
        search: Optional[str] = None,
        serial_number: Optional[str] = None,
        author: Optional[str] = None,
        category: Optional[str] = None,
        language: Optional[str] = None,
        status: Optional[str] = None,
        publish_on_website: Optional[bool] = None,
    ) -> StreamingResponse:

        books_col = get_books_collection()

        # ---------------------------------------------------------
        # 1. Validate selected fields
        # ---------------------------------------------------------

        if not fields:
            fields = list(CSVExportService.AVAILABLE_FIELDS.keys())

        invalid_fields = [
            field
            for field in fields
            if field not in CSVExportService.AVAILABLE_FIELDS
        ]

        if invalid_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid export fields: {', '.join(invalid_fields)}"
            )

        # Remove duplicates while preserving order
        fields = list(dict.fromkeys(fields))

        if not fields:
            raise HTTPException(
                status_code=400,
                detail="At least one field must be selected for export."
            )

        # ---------------------------------------------------------
        # 2. Build MongoDB filter
        # ---------------------------------------------------------

        query: Dict[str, Any] = {}

        if search and search.strip():
            search_term = search.strip()

            query["$or"] = [
                {
                    "title": {
                        "$regex": search_term,
                        "$options": "i"
                    }
                },
                {
                    "author": {
                        "$regex": search_term,
                        "$options": "i"
                    }
                },
                {
                    "author_alias": {
                        "$regex": search_term,
                        "$options": "i"
                    }
                },
                {
                    "series_name": {
                        "$regex": search_term,
                        "$options": "i"
                    }
                },
                {
                    "book_id": {
                        "$regex": search_term,
                        "$options": "i"
                    }
                }
            ]

        if serial_number and serial_number.strip():
            query["serial_number"] = serial_number.strip()

        if author and author.strip():
            query["$and"] = query.get("$and", [])

            query["$and"].append({
                "$or": [
                    {
                        "author": {
                            "$regex": author.strip(),
                            "$options": "i"
                        }
                    },
                    {
                        "author_alias": {
                            "$regex": author.strip(),
                            "$options": "i"
                        }
                    }
                ]
            })

        if category:
            query["category"] = category

        if language:
            query["language"] = language

        if status:
            query["status"] = status

        if publish_on_website is not None:
            query["publish_on_website"] = publish_on_website

        # ---------------------------------------------------------
        # 3. Fetch ALL matching books
        # ---------------------------------------------------------

        projection = {
            field: 1
            for field in fields
        }

        cursor = books_col.find(
            query,
            projection
        ).sort("serial_number", 1)

        books = await cursor.to_list(length=None)

        # ---------------------------------------------------------
        # 4. Generate UTF-8 CSV
        # ---------------------------------------------------------

        output = io.StringIO(
            newline=""
        )

        writer = csv.writer(
            output,
            quoting=csv.QUOTE_MINIMAL
        )

        # Header row
        writer.writerow([
            CSVExportService.AVAILABLE_FIELDS[field]
            for field in fields
        ])

        # Data rows
        for book in books:

            row = []

            for field in fields:

                value = book.get(field, "")

                if value is None:
                    value = ""

                # Convert datetime values to ISO format
                if hasattr(value, "isoformat"):
                    value = value.isoformat()

                row.append(value)

            writer.writerow(row)

        # ---------------------------------------------------------
        # 5. UTF-8 BOM
        # ---------------------------------------------------------
        #
        # This makes the CSV open correctly in Microsoft Excel
        # while preserving Tamil and other Unicode characters.
        #

        csv_content = "\ufeff" + output.getvalue()

        output.close()

        # ---------------------------------------------------------
        # 6. Return downloadable CSV
        # ---------------------------------------------------------

        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": (
                    'attachment; filename="library_books.csv"'
                )
            }
        )