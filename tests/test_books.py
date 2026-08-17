import pytest
import io

@pytest.mark.asyncio
async def test_create_book_and_unique_id(async_client, admin_auth_headers):
    # 1. Create English Book
    payload1 = {
        "title": "The Alchemist",
        "author": "Paulo Coelho",
        "price": 250.0,
        "category": "Fiction",
        "language": "English",
        "publish_on_website": True
    }
    response1 = await async_client.post("/api/admin/books", json=payload1, headers=admin_auth_headers)
    assert response1.status_code == 201
    data1 = response1.json()
    assert data1["book_id"] == "LIB-00001"
    assert data1["status"] == "available"

    # 2. Create Tamil Book (Unicode test)
    payload2 = {
        "title": "தெய்வத்தின் குரல்",
        "author": "காஞ்சி பரமாச்சாரியார்",
        "price": 450.0,
        "category": "Philosophy",
        "language": "Tamil",
        "publish_on_website": False
    }
    response2 = await async_client.post("/api/admin/books", json=payload2, headers=admin_auth_headers)
    assert response2.status_code == 201
    data2 = response2.json()
    assert data2["book_id"] == "LIB-00002"
    assert data2["title"] == "தெய்வத்தின் குரல்"
    assert data2["author"] == "காஞ்சி பரமாச்சாரியார்"

@pytest.mark.asyncio
async def test_search_and_filter_books(async_client, admin_auth_headers):
    # Create books for search/filter
    payload1 = {
        "title": "The Alchemist",
        "author": "Paulo Coelho",
        "price": 250.0,
        "category": "Fiction",
        "language": "English",
        "publish_on_website": True
    }
    await async_client.post("/api/admin/books", json=payload1, headers=admin_auth_headers)

    payload2 = {
        "title": "தெய்வத்தின் குரல்",
        "author": "காஞ்சி பரமாச்சாரியார்",
        "price": 450.0,
        "category": "Philosophy",
        "language": "Tamil",
        "publish_on_website": False
    }
    await async_client.post("/api/admin/books", json=payload2, headers=admin_auth_headers)

    # Search Tamil title
    response = await async_client.get("/api/admin/books?search=தெய்வத்தின்", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "தெய்வத்தின் குரல்"

    # Filter language=English
    res_lang = await async_client.get("/api/admin/books?language=English", headers=admin_auth_headers)
    assert res_lang.status_code == 200
    assert res_lang.json()["total"] == 1

@pytest.mark.asyncio
async def test_csv_import_with_partial_records_and_optional_fields(async_client, admin_auth_headers):
    csv_content = (
        "title,author,price,category,language,series_name,volume_number,total_volumes\n"
        "November 9,Colleen Hoover,,English Fiction,English,,\n"
        "Some Tamil Book,,,Tamil Spiritual,Tamil,,\n"
        "Some Book,,,,,,\n"
        "தேவ ரகசியம்,காஞ்சி பரமாச்சாரியார்,300,Philosophy,Tamil,,\n"
        "Diary of a Wimpy Kid,Jeff Kinney,499.50,Children,English,Wimpy Kid,1,17\n"
    )
    files = {"file": ("books.csv", csv_content.encode("utf-8"), "text/csv")}
    
    # Test Preview Mode (preview=true)
    preview_res = await async_client.post("/api/admin/books/import?preview=true", files=files, headers=admin_auth_headers)
    assert preview_res.status_code == 200
    preview_data = preview_res.json()
    assert preview_data["total_rows"] == 5
    assert preview_data["imported"] == 5
    assert preview_data["failed"] == 0

    # Execute actual import (preview=false)
    files = {"file": ("books.csv", csv_content.encode("utf-8"), "text/csv")}
    import_res = await async_client.post("/api/admin/books/import?preview=false", files=files, headers=admin_auth_headers)
    assert import_res.status_code == 200
    import_data = import_res.json()
    assert import_data["imported"] == 5

    # Verify "Some Book" with missing author, price, category, language
    res_some = await async_client.get("/api/admin/books?search=Some Book", headers=admin_auth_headers)
    assert res_some.status_code == 200
    book = res_some.json()["items"][0]
    assert book["title"] == "Some Book"
    assert book["author"] is None
    assert book["price"] is None
    assert book["category"] is None
    assert book["language"] is None

@pytest.mark.asyncio
async def test_csv_import_validation_errors(async_client, admin_auth_headers):
    csv_content = (
        "title,author,price,category,language\n"
        ",Colleen Hoover,250,Fiction,English\n"  # Missing title (Invalid)
        "Invalid Price Book,Author,abc,Category,Language\n"  # Invalid price (Invalid)
        "Rupee Price Book,Author,₹250,Category,Language\n"  # Invalid price (Invalid)
        "Valid Book,Author,150,Category,Language\n"  # Valid
    )
    files = {"file": ("books.csv", csv_content.encode("utf-8"), "text/csv")}
    response = await async_client.post("/api/admin/books/import?preview=true", files=files, headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 4
    assert data["imported"] == 1
    assert data["failed"] == 3

    errors = data["errors"]
    assert any(e["row"] == 2 and e["field"] == "title" and "Title is required" in e["message"] for e in errors)
    assert any(e["row"] == 3 and e["field"] == "price" and "Price must be a valid number" in e["message"] for e in errors)
    assert any(e["row"] == 4 and e["field"] == "price" and "Price must be a valid number" in e["message"] for e in errors)
