import pytest

@pytest.mark.asyncio
async def test_public_api_isolation(async_client, admin_auth_headers):
    # 1. Create a Published Book
    pub_book = {
        "title": "Public Visible Book",
        "author": "Public Author",
        "price": 199.0,
        "category": "General",
        "language": "English",
        "publish_on_website": True
    }
    p_res = await async_client.post("/api/admin/books", json=pub_book, headers=admin_auth_headers)
    assert p_res.status_code == 201
    pub_id = p_res.json()["book_id"]

    # 2. Create an Unpublished Book
    unpub_book = {
        "title": "Secret Internal Book",
        "author": "Private Author",
        "price": 999.0,
        "category": "Internal",
        "language": "English",
        "publish_on_website": False
    }
    u_res = await async_client.post("/api/admin/books", json=unpub_book, headers=admin_auth_headers)
    assert u_res.status_code == 201
    unpub_id = u_res.json()["book_id"]

    # 3. Query Public API `/api/books` without auth
    public_res = await async_client.get("/api/books")
    assert public_res.status_code == 200
    public_data = public_res.json()

    book_ids = [b["book_id"] for b in public_data["items"]]
    assert pub_id in book_ids
    assert unpub_id not in book_ids

    # 4. Try fetching unpublished book directly from public API -> should return 404
    direct_unpub = await async_client.get(f"/api/books/{unpub_id}")
    assert direct_unpub.status_code == 404


@pytest.mark.asyncio
async def test_public_catalog_search_and_unicode(async_client, admin_auth_headers):
    # 1. Create a published book titled "The Alchemist"
    alchemist_book = {
        "title": "The Alchemist",
        "author": "Paulo Coelho",
        "price": 250.0,
        "category": "Fiction",
        "language": "English",
        "publish_on_website": True
    }
    a_res = await async_client.post("/api/admin/books", json=alchemist_book, headers=admin_auth_headers)
    assert a_res.status_code == 201
    alchemist_id = a_res.json()["book_id"]

    # 2. Create a published Tamil book with Tamil Unicode title
    tamil_title = "சிவகாமி யின் சபதம்"
    tamil_author = "கல்கி"
    tamil_book = {
        "title": tamil_title,
        "author": tamil_author,
        "price": 400.0,
        "category": "Historical",
        "language": "Tamil",
        "publish_on_website": True
    }
    t_res = await async_client.post("/api/admin/books", json=tamil_book, headers=admin_auth_headers)
    assert t_res.status_code == 201
    tamil_id = t_res.json()["book_id"]

    # 3. Create a series published books
    series_vol1 = {
        "title": "Harry Potter 1",
        "author": "JK Rowling",
        "series_name": "Harry Potter",
        "volume_number": "1",
        "category": "Fantasy",
        "language": "English",
        "publish_on_website": True
    }
    series_vol2 = {
        "title": "Harry Potter 2",
        "author": "JK Rowling",
        "series_name": "Harry Potter",
        "volume_number": "2",
        "category": "Fantasy",
        "language": "English",
        "publish_on_website": True
    }
    await async_client.post("/api/admin/books", json=series_vol1, headers=admin_auth_headers)
    await async_client.post("/api/admin/books", json=series_vol2, headers=admin_auth_headers)

    # Test GET /api/books/catalog?limit=200
    res_cat = await async_client.get("/api/books/catalog?limit=200")
    assert res_cat.status_code == 200
    cat_data = res_cat.json()
    assert cat_data["total"] > 0

    # Test Unicode in response
    found_tamil = False
    for item in cat_data["items"]:
        if item.get("book_id") == tamil_id:
            assert item["title"] == tamil_title
            assert item["author"] == tamil_author
            found_tamil = True
    assert found_tamil, "Tamil book was not found in catalog items"

    # Test search=Alchemist
    res_alchemist = await async_client.get("/api/books/catalog?search=Alchemist&limit=200")
    assert res_alchemist.status_code == 200
    alchemist_items = res_alchemist.json()["items"]
    assert any(b.get("book_id") == alchemist_id or b.get("title") == "The Alchemist" for b in alchemist_items)

    # Test Tamil search search=சிவகாமி
    res_tamil_search = await async_client.get(f"/api/books/catalog?search={tamil_title[:6]}&limit=200")
    assert res_tamil_search.status_code == 200
    tamil_search_items = res_tamil_search.json()["items"]
    assert any(b.get("book_id") == tamil_id for b in tamil_search_items)

    # Test Category + Search together
    res_cat_search = await async_client.get("/api/books/catalog?search=Alchemist&category=Fiction&limit=200")
    assert res_cat_search.status_code == 200
    assert any(b.get("book_id") == alchemist_id for b in res_cat_search.json()["items"])

    # Test Language + Search together
    res_lang_search = await async_client.get(f"/api/books/catalog?search={tamil_title[:6]}&language=Tamil&limit=200")
    assert res_lang_search.status_code == 200
    assert any(b.get("book_id") == tamil_id for b in res_lang_search.json()["items"])

    # Test Series Grouping
    res_series = await async_client.get("/api/books/catalog?search=Harry%20Potter&limit=200")
    assert res_series.status_code == 200
    series_items = res_series.json()["items"]
    assert len(series_items) == 1
    assert series_items[0]["type"] == "series"
    assert series_items[0]["series_name"] == "Harry Potter"
    assert series_items[0]["total_volumes"] == 2

