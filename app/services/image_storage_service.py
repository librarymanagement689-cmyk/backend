import os
import uuid
import logging
from typing import Optional
from fastapi import UploadFile, HTTPException, status

logger = logging.getLogger("image_storage")

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

class ImageStorageService:
    @staticmethod
    async def save_image(file: UploadFile) -> str:
        """
        Validates file type and size.
        Saves file to local static directory (or uploads to Cloudflare R2 if configured).
        Returns the public image URL.
        """
        if not file.filename:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file filename provided")

        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS or file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid image format. Allowed formats: JPG, JPEG, PNG, WebP"
            )

        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size exceeds maximum allowed limit of 5 MB"
            )

        # Generate unique filename
        filename = f"cover_{uuid.uuid4().hex[:12]}{ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        with open(file_path, "wb") as f:
            f.write(contents)

        logger.info(f"Saved cover image to {file_path}")

        # Return public URL (static upload route)
        return f"http://localhost:8000/static/uploads/{filename}"

    @staticmethod
    async def delete_image(image_url: Optional[str]) -> bool:
        """
        Removes stored image file if it belongs to local static uploads.
        """
        if not image_url or "/static/uploads/" not in image_url:
            return False

        try:
            filename = image_url.split("/static/uploads/")[-1]
            file_path = os.path.join(UPLOAD_DIR, filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted cover image at {file_path}")
                return True
        except Exception as e:
            logger.error(f"Error deleting image {image_url}: {e}")

        return False
