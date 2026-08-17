from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException
)

from app.services.r2_service import R2Service


router = APIRouter(
    prefix="/api/admin/r2",
    tags=["Admin R2 Storage"]
)


# ============================================================
# TEST CONNECTION
# ============================================================

@router.get("/test")
async def test_r2():

    try:

        service = R2Service()

        return service.test_connection()

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"R2 connection failed: {str(e)}"
        )


# ============================================================
# UPLOAD BOOK IMAGE
# ============================================================

@router.post(
    "/books/{book_id}/image"
)
async def upload_book_image(
    book_id: str,
    file: UploadFile = File(...)
):

    # --------------------------------------------------------
    # Validate MIME type
    # --------------------------------------------------------

    allowed_types = {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif"
    }

    if file.content_type not in allowed_types:

        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported image type. "
                "Allowed: JPG, PNG, WEBP, GIF"
            )
        )

    # --------------------------------------------------------
    # Validate file size
    # --------------------------------------------------------

    max_size = 10 * 1024 * 1024  # 10 MB

    content = await file.read()

    if len(content) > max_size:

        raise HTTPException(
            status_code=400,
            detail="Image size cannot exceed 10 MB"
        )

    # Reset file pointer
    await file.seek(0)

    # --------------------------------------------------------
    # Upload
    # --------------------------------------------------------

    try:

        service = R2Service()

        result = await service.upload_book_cover(
            book_id=book_id,
            file=file,
            filename=file.filename,
            content_type=file.content_type
        )

        return result

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Image upload failed: {str(e)}"
        )


# ============================================================
# DELETE BOOK IMAGE
# ============================================================

@router.delete(
    "/books/{book_id}/image"
)
async def delete_book_image(
    book_id: str
):

    try:

        service = R2Service()

        return service.delete_book_cover(
            book_id
        )

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Image deletion failed: {str(e)}"
        )