from typing import Optional
from fastapi import APIRouter, Depends, Query, File, UploadFile, HTTPException, status
from app.schemas.book import (
    BookCreate, BookUpdate, BookResponse, BookPaginatedResponse, CSVImportSummaryResponse
)
from app.services.book_service import BookService
from app.services.csv_import_service import CSVImportService
from app.auth.dependencies import get_current_admin
from app.services.book_service import BookService

router = APIRouter(prefix="/api/admin/books", tags=["Admin Books"])

@router.post("", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(
    data: BookCreate,
    current_admin: dict = Depends(get_current_admin)
):
    return await BookService.create_book(data)

@router.get("", response_model=BookPaginatedResponse)
async def get_books(
    search: Optional[str] = Query(None, description="Search title, author, or book_id"),
    author: Optional[str] = Query(None, description="Filter by author"),
    serial_number: Optional[str] = Query(None, description="Filter by library serial number"),
    category: Optional[str] = Query(None, description="Filter by category"),
    language: Optional[str] = Query(None, description="Filter by language"),
    status: Optional[str] = Query(None, description="available or borrowed"),
    publish_on_website: Optional[bool] = Query(None, description="Filter by publication status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    current_admin: dict = Depends(get_current_admin)
):
    return await BookService.get_books(
        search=search,
        serial_number=serial_number,
        author=author,
        category=category,
        language=language,
        status=status,
        publish_on_website=publish_on_website,
        page=page,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order
    )

@router.post("/upload-image")
async def upload_book_cover(
    file: UploadFile = File(...),
    current_admin: dict = Depends(get_current_admin)
):
    from app.services.image_storage_service import ImageStorageService
    image_url = await ImageStorageService.save_image(file)
    return {"image_url": image_url, "filename": file.filename}

@router.delete("/{book_id}/image")
async def delete_book_cover(
    book_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    from app.services.image_storage_service import ImageStorageService
    book = await BookService.get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

    old_url = book.get("image_url")
    if old_url:
        await ImageStorageService.delete_image(old_url)
        await BookService.update_book(book_id, BookUpdate(image_url=None))

    return {"message": f"Cover image for {book_id} removed successfully", "success": True}

@router.post("/import", response_model=CSVImportSummaryResponse)
async def import_books_csv(
    file: UploadFile = File(...),
    preview: bool = Query(False, description="If true, only validate CSV without inserting into database"),
    current_admin: dict = Depends(get_current_admin)
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")
    
    contents = await file.read()
    return await CSVImportService.process_csv(contents, preview_only=preview)

@router.get("/{book_id}", response_model=BookResponse)
async def get_book(
    book_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    book = await BookService.get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")
    return book

@router.put("/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: str,
    data: BookUpdate,
    current_admin: dict = Depends(get_current_admin)
):
    return await BookService.update_book(book_id, data)

@router.delete("/{book_id}", status_code=status.HTTP_200_OK)
async def delete_book(
    book_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    success = await BookService.delete_book(book_id)
    return {"message": f"Book {book_id} deleted successfully", "success": success}

@router.get("/{book_id}/history")
async def get_book_borrowing_history(
    book_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    return await BookService.get_book_borrowing_history(book_id)
