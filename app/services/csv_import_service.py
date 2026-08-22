import csv
import io
from typing import List, Dict, Any, Tuple

from app.database import get_books_collection
from app.utils.helpers import generate_unique_id, current_utc_datetime


class CSVImportService:
    @staticmethod
    async def process_csv(
        csv_bytes: bytes,
        preview_only: bool = False
    ) -> Dict[str, Any]:
        """
        Parses UTF-8 CSV for bulk book import.

        Required:
        - title

        Optional:
        - author
        - price
        - category
        - language
        - image_url
        - part_or_volume
        - series_name
        - volume_number
        - total_volumes

        Important:
        - CSV must be UTF-8 encoded.
        - UTF-8 BOM is supported.
        - Tamil and other Unicode characters are preserved.
        - Missing optional values are stored as None.
        - Missing price is NOT converted to 0.
        - Invalid encoding is rejected instead of silently corrupting data.
        """

        # ============================================================
        # 1. DECODE CSV SAFELY AS UTF-8
        # ============================================================
        #
        # utf-8-sig supports:
        #   - normal UTF-8
        #   - UTF-8 files with BOM (common with Excel)
        #
        # DO NOT fall back to cp1252 / latin-1.
        # Those encodings can silently interpret invalid UTF-8 bytes
        # and corrupt Tamil/Unicode data.
        #
        # DO NOT use errors="replace".
        #

        try:
            content_str = csv_bytes.decode("utf-8-sig")

        except UnicodeDecodeError:
            return {
                "total_rows": 0,
                "imported": 0,
                "failed": 0,
                "errors": [
                    {
                        "row": 0,
                        "field": "file",
                        "message": (
                            "CSV file must be UTF-8 encoded. "
                            "Please save the file as CSV UTF-8."
                        )
                    }
                ]
            }

        # ============================================================
        # 2. CREATE CSV READER
        # ============================================================

        reader = csv.DictReader(
            io.StringIO(content_str, newline="")
        )

        # ============================================================
        # 3. NORMALIZE HEADERS
        # ============================================================

        raw_fieldnames = reader.fieldnames or []

        fieldnames = [
            f.strip().lower()
            for f in raw_fieldnames
            if f
        ]

        required_fields = [
            "serial_number",
            "title"
        ]

        missing_fields = [
            field for field in required_fields
            if field not in fieldnames
        ]

        if missing_fields:
            return {
                "total_rows": 0,
                "imported": 0,
                "failed": 0,
                "errors": [
                    {
                        "row": 0,
                        "field": "header",
                        "message": (
                            f"CSV missing required fields: "
                            f"{', '.join(missing_fields)}"
                        )
                    }
                ]
            }

        # ============================================================
        # 4. PROCESS ROWS
        # ============================================================

        valid_books: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []

        # Header is row 1.
        # First data row is row 2.
        row_num = 1

        for row in reader:
            row_num += 1

            # --------------------------------------------------------
            # Skip completely empty rows
            # --------------------------------------------------------

            if not row:
                continue

            if not any(
                v is not None and str(v).strip()
                for v in row.values()
            ):
                continue

            # --------------------------------------------------------
            # Normalize row keys and values
            # --------------------------------------------------------

            row_clean: Dict[str, str] = {}

            for key, value in row.items():
                if not key:
                    continue

                normalized_key = key.strip().lower()

                if value is None:
                    normalized_value = ""
                else:
                    normalized_value = str(value).strip()

                row_clean[normalized_key] = normalized_value

            # --------------------------------------------------------
            # Extract fields
            # --------------------------------------------------------

            title = row_clean.get("title", "").strip()
            serial_number_raw = row_clean.get("serial_number", "").strip()

            author_raw = row_clean.get("author", "").strip()
            author_alias_raw = row_clean.get("author_alias", "").strip()

            price_raw = row_clean.get("price", "").strip()

            category_raw = row_clean.get("category", "").strip()
            language_raw = row_clean.get("language", "").strip()

            part_or_vol_raw = (
                row_clean.get("part_or_volume", "").strip()
            )

            series_name_raw = (
                row_clean.get("series_name", "").strip()
            )

            volume_num_raw = (
                row_clean.get("volume_number", "").strip()
            )

            total_vols_raw = (
                row_clean.get("total_volumes", "").strip()
            )

            image_url_raw = (
                row_clean.get("image_url", "").strip()
            )

            row_valid = True

# ========================================================
# EMPTY CATALOGUE SLOT
# ========================================================
# If there is no title, this serial number represents
# an empty slot in the physical register.
# Do not import it and do not report it as an error.

            if not title:
                continue

            # ========================================================
            # SERIAL NUMBER VALIDATION
            # ========================================================

            serial_number = None

            if not serial_number_raw:
                errors.append(
                    {
                        "row": row_num,
                        "field": "serial_number",
                        "message": "Serial number is required for a book"
                        }
                    )
                row_valid = False
            else:
                # Serial numbers are catalogue identifiers, not numbers.
                # Preserve values such as:
                # 1, 25, 11A, 19A, 16.A
                serial_number = serial_number_raw

            # ========================================================
            # 5. TITLE VALIDATION
            # ========================================================

            # ========================================================
            # 6. AUTHOR - OPTIONAL
            # ========================================================

            author = author_raw if author_raw else None

            # ========================================================
            # 7. PRICE - OPTIONAL
            # ========================================================

            price_val = None

            if price_raw:

                try:
                    price_val = float(price_raw)

                    if price_val < 0:
                        errors.append(
                            {
                                "row": row_num,
                                "field": "price",
                                "message": "Price cannot be negative"
                            }
                        )

                        row_valid = False

                except (ValueError, TypeError):

                    errors.append(
                        {
                            "row": row_num,
                            "field": "price",
                            "message": "Price must be a valid number"
                        }
                    )

                    row_valid = False

            # ========================================================
            # 8. OPTIONAL FIELDS
            # ========================================================

            category = (
                category_raw
                if category_raw
                else None
            )

            language = (
                language_raw
                if language_raw
                else None
            )

            part_or_volume = (
                part_or_vol_raw
                if part_or_vol_raw
                else None
            )

            series_name = (
                series_name_raw
                if series_name_raw
                else None
            )

            volume_number = (
                volume_num_raw
                if volume_num_raw
                else None
            )

            total_volumes = (
                total_vols_raw
                if total_vols_raw
                else None
            )

            image_url = (
                image_url_raw
                if image_url_raw
                else None
            )

            # ========================================================
            # 9. ADD VALID BOOK
            # ========================================================

            if row_valid:

                valid_books.append(
                    {
                        "row_num": row_num,
                        "serial_number": serial_number,
                        "author_alias": author_alias_raw if author_alias_raw else None,
                        "title": title,
                        "author": author,
                        "price": price_val,
                        "category": category,
                        "language": language,
                        "part_or_volume": part_or_volume,
                        "series_name": series_name,
                        "volume_number": volume_number,
                        "total_volumes": total_volumes,
                        "image_url": image_url
                    }
                )

        # ============================================================
        # 10. COUNTS
        # ============================================================

        total_rows = row_num - 1

        # Count unique invalid rows.
        # Multiple errors on one row still count as one invalid row.

        invalid_rows_set = {
            err["row"]
            for err in errors
            if err["row"] > 0
        }

        failed_count = len(invalid_rows_set)

        imported_count = 0

        # ============================================================
        # 11. IMPORT INTO MONGODB
        # ============================================================

        if not preview_only and valid_books:

            books_col = get_books_collection()

            now = current_utc_datetime()

            documents_to_insert = []

            for book_item in valid_books:

                # Generate unique LIB-XXXXX ID
                book_id = await generate_unique_id(
                    "book_id",
                    "LIB",
                    5
                )

                documents_to_insert.append(
                    {
                        "book_id": book_id,

                        "serial_number": book_item["serial_number"],

                        # Preserve Unicode exactly as received
                        "title": book_item["title"],

                        "author": book_item["author"],

                        "author_alias": book_item["author_alias"],

                        # Missing price remains None
                        "price": book_item["price"],

                        "category": book_item["category"],

                        "language": book_item["language"],

                        "part_or_volume": (
                            book_item["part_or_volume"]
                        ),

                        "series_name": (
                            book_item["series_name"]
                        ),

                        "volume_number": (
                            book_item["volume_number"]
                        ),

                        "total_volumes": (
                            book_item["total_volumes"]
                        ),

                        "status": "available",

                        # Newly imported books are published by default.
                        "publish_on_website": True,

                        "image_url": (
                            book_item["image_url"]
                        ),

                        "created_at": now,
                        "updated_at": now
                    }
                )

            if documents_to_insert:

                await books_col.insert_many(
                    documents_to_insert
                )

                imported_count = len(
                    documents_to_insert
                )

        else:
            # Preview mode:
            # report valid rows but DO NOT insert into MongoDB.
            imported_count = len(valid_books)

        # ============================================================
        # 12. RETURN RESULT
        # ============================================================

        return {
            "total_rows": total_rows,
            "imported": imported_count,
            "failed": failed_count,
            "errors": errors
        }
        