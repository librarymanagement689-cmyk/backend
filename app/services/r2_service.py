import os
import re
from typing import Optional

import boto3
from botocore.exceptions import ClientError


class R2Service:

    def __init__(self):
        self.account_id = os.getenv("R2_ACCOUNT_ID")
        self.access_key_id = os.getenv("R2_ACCESS_KEY_ID")
        self.secret_access_key = os.getenv("R2_SECRET_ACCESS_KEY")
        self.bucket_name = os.getenv("R2_BUCKET_NAME")
        self.endpoint_url = os.getenv("R2_ENDPOINT_URL")
        self.public_url = os.getenv("R2_PUBLIC_URL", "").rstrip("/")

        if not self.access_key_id:
            raise RuntimeError("R2_ACCESS_KEY_ID is not configured")

        if not self.secret_access_key:
            raise RuntimeError("R2_SECRET_ACCESS_KEY is not configured")

        if not self.bucket_name:
            raise RuntimeError("R2_BUCKET_NAME is not configured")

        if not self.endpoint_url:
            raise RuntimeError("R2_ENDPOINT_URL is not configured")

        if not self.public_url:
            raise RuntimeError("R2_PUBLIC_URL is not configured")

        self.client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name="auto"
        )

    # ========================================================
    # VALIDATE BOOK ID
    # ========================================================

    @staticmethod
    def validate_book_id(book_id: str) -> str:

        book_id = book_id.strip()

        if not re.fullmatch(
            r"LIB-\d{5}",
            book_id
        ):
            raise ValueError(
                "Invalid book ID format"
            )

        return book_id

    # ========================================================
    # NORMALIZE EXTENSION
    # ========================================================

    @staticmethod
    def get_extension(
        filename: Optional[str],
        content_type: Optional[str]
    ) -> str:

        filename = filename or ""

        extension = os.path.splitext(
            filename
        )[1].lower()

        allowed_extensions = {
            ".jpg": ".jpg",
            ".jpeg": ".jpg",
            ".png": ".png",
            ".webp": ".webp",
            ".gif": ".gif"
        }

        if extension in allowed_extensions:
            return allowed_extensions[extension]

        content_type_map = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif"
        }

        if content_type in content_type_map:
            return content_type_map[content_type]

        raise ValueError(
            "Unsupported image type. "
            "Allowed: JPG, PNG, WEBP, GIF"
        )

    # ========================================================
    # DELETE EXISTING BOOK IMAGES
    # ========================================================

    def delete_book_images(
        self,
        book_id: str
    ) -> int:

        book_id = self.validate_book_id(
            book_id
        )

        prefix = f"books/{book_id}/"

        response = self.client.list_objects_v2(
            Bucket=self.bucket_name,
            Prefix=prefix
        )

        objects = response.get(
            "Contents",
            []
        )

        if not objects:
            return 0

        delete_payload = {
            "Objects": [
                {
                    "Key": obj["Key"]
                }
                for obj in objects
            ]
        }

        self.client.delete_objects(
            Bucket=self.bucket_name,
            Delete=delete_payload
        )

        return len(objects)

    # ========================================================
    # UPLOAD BOOK COVER
    # ========================================================

    async def upload_book_cover(
        self,
        book_id: str,
        file,
        filename: Optional[str],
        content_type: Optional[str]
    ) -> dict:

        book_id = self.validate_book_id(
            book_id
        )

        extension = self.get_extension(
            filename,
            content_type
        )

        # ----------------------------------------------------
        # Remove previous image(s)
        # ----------------------------------------------------

        self.delete_book_images(
            book_id
        )

        # ----------------------------------------------------
        # Standard object key
        # ----------------------------------------------------

        object_key = (
            f"books/{book_id}/cover{extension}"
        )

        # ----------------------------------------------------
        # Upload
        # ----------------------------------------------------

        file.file.seek(0)

        self.client.upload_fileobj(
            file.file,
            self.bucket_name,
            object_key,
            ExtraArgs={
                "ContentType": content_type
                or "application/octet-stream",

                "CacheControl": (
                    "public, max-age=31536000"
                )
            }
        )

        public_url = (
            f"{self.public_url}/{object_key}"
        )

        return {
            "success": True,
            "book_id": book_id,
            "key": object_key,
            "url": public_url
        }

    # ========================================================
    # DELETE BOOK COVER
    # ========================================================

    def delete_book_cover(
        self,
        book_id: str
    ) -> dict:

        book_id = self.validate_book_id(
            book_id
        )

        deleted = self.delete_book_images(
            book_id
        )

        return {
            "success": True,
            "book_id": book_id,
            "deleted_objects": deleted
        }

    # ========================================================
    # CHECK R2 CONNECTION
    # ========================================================

    def test_connection(self) -> dict:

        response = self.client.list_objects_v2(
            Bucket=self.bucket_name,
            MaxKeys=1
        )

        return {
            "success": True,
            "bucket": self.bucket_name,
            "objects": response.get(
                "KeyCount",
                0
            )
        }