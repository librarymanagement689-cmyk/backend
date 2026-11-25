import pytest
import time
from datetime import date, timedelta

@pytest.mark.asyncio
async def test_order_creation_price_snapshot_and_returns(async_client, admin_auth_headers):
    # 0. Create Subscription Plan
    sub_payload = {
        "name": "Standard Monthly",
        "description": "Basic 30-day access",
        "duration_days": 30,
        "price": 150.0,
        "is_active": True
    }
    sub_res = await async_client.post("/api/admin/subscriptions", json=sub_payload, headers=admin_auth_headers)
    assert sub_res.status_code == 201
    sub_id = sub_res.json()["subscription_id"]

    # 1. Create a Book with price ₹250
    book_payload = {
        "serial_number": "SN-TEST-01",
        "title": "Master Price Test Book",
        "author": "Author X",
        "price": 250.0,
        "category": "Test",
        "language": "English",
        "publish_on_website": True
    }
    b_res = await async_client.post("/api/admin/books", json=book_payload, headers=admin_auth_headers)
    assert b_res.status_code == 201
    book_data = b_res.json()
    book_id = book_data["book_id"]

    import time
    unique_ts = time.time_ns()
    # 2. Create Member
    today = date.today()
    mem_payload = {
        "name": "Order Test Member",
        "phone": "+91 99999 88888",
        "email": f"ordertest_{unique_ts}@example.com",
        "subscription_type_id": sub_id,
        "subscription_start_date": today.isoformat(),
        "subscription_end_date": (today + timedelta(days=30)).isoformat(),
        "status": "active"
    }
    m_res = await async_client.post("/api/admin/members", json=mem_payload, headers=admin_auth_headers)
    assert m_res.status_code == 201
    member_id = m_res.json()["member_id"]

    # 3. Create Order
    b_date = today.isoformat()
    d_date = (today + timedelta(days=7)).isoformat()
    order_payload = {
        "member_id": member_id,
        "items": [{"book_id": book_id}],
        "borrowed_date": b_date,
        "due_date": d_date,
        "amount_paid": 30.0
    }
    o_res = await async_client.post("/api/admin/orders", json=order_payload, headers=admin_auth_headers)
    assert o_res.status_code == 201
    order_data = o_res.json()
    order_id = order_data["order_id"]
    assert order_data["subtotal"] == 30.0
    assert order_data["items"][0]["price"] == 250.0
    assert order_data["items"][0]["lending_amount"] == 30.0

    # Verify book status changed to borrowed
    b_check = await async_client.get(f"/api/admin/books/{book_id}", headers=admin_auth_headers)
    assert b_check.json()["status"] == "borrowed"

    # 4. MANDATORY PRICE IMMUTABILITY TEST: Change master book price from ₹250 to ₹300
    update_book_res = await async_client.put(
        f"/api/admin/books/{book_id}",
        json={"price": 300.0},
        headers=admin_auth_headers
    )
    assert update_book_res.status_code == 200
    assert update_book_res.json()["price"] == 300.0

    # Verify old order STILL shows ₹250
    o_check = await async_client.get(f"/api/admin/orders/{order_id}", headers=admin_auth_headers)
    assert o_check.status_code == 200
    fetched_order = o_check.json()
    assert fetched_order["subtotal"] == 30.0
    assert fetched_order["items"][0]["price"] == 250.0

    # 5. Return book
    return_res = await async_client.post(
        f"/api/admin/orders/{order_id}/return",
        json={"book_ids": [book_id]},
        headers=admin_auth_headers
    )
    assert return_res.status_code == 200
    assert return_res.json()["status"] == "returned"

    # Verify book status changed back to available
    b_avail = await async_client.get(f"/api/admin/books/{book_id}", headers=admin_auth_headers)
    assert b_avail.json()["status"] == "available"


@pytest.mark.asyncio
async def test_order_rental_calculation_6_books_1000_mrp_120_rental(async_client, admin_auth_headers):
    # 0. Create Subscription Plan
    sub_payload = {
        "name": "Standard Monthly Plan",
        "description": "Basic monthly access",
        "duration_days": 30,
        "price": 100.0,
        "is_active": True
    }
    sub_res = await async_client.post("/api/admin/subscriptions", json=sub_payload, headers=admin_auth_headers)
    assert sub_res.status_code == 201
    sub_id = sub_res.json()["subscription_id"]

    # 1. Create Member
    today = date.today()
    mem_payload = {
        "name": "6 Books Test Member",
        "phone": "+91 98888 77777",
        "email": f"books6test_{time.time_ns()}@example.com",
        "subscription_type_id": sub_id,
        "subscription_start_date": today.isoformat(),
        "subscription_end_date": (today + timedelta(days=30)).isoformat(),
        "status": "active"
    }
    m_res = await async_client.post("/api/admin/members", json=mem_payload, headers=admin_auth_headers)
    assert m_res.status_code == 201
    member_id = m_res.json()["member_id"]

    # 2. Create 6 books totaling MRP ₹1,000
    prices = [200.0, 200.0, 150.0, 150.0, 150.0, 150.0]
    book_ids = []
    for idx, p in enumerate(prices, 1):
        b_res = await async_client.post("/api/admin/books", json={
            "serial_number": f"SN-6B-0{idx}",
            "title": f"Test Book {idx}",
            "author": "Author Y",
            "price": p,
            "category": "General",
            "language": "English",
            "publish_on_website": True
        }, headers=admin_auth_headers)
        assert b_res.status_code == 201
        book_ids.append(b_res.json()["book_id"])

    # 3. Create Order for all 6 books
    order_res = await async_client.post("/api/admin/orders", json={
        "member_id": member_id,
        "book_ids": book_ids,
        "borrowed_date": today.isoformat(),
        "due_date": (today + timedelta(days=14)).isoformat(),
        "amount_paid": 120.0
    }, headers=admin_auth_headers)

    assert order_res.status_code == 201
    o_data = order_res.json()
    assert o_data["total_mrp"] == 1000.0
    assert o_data["rental_amount"] == 120.0
    assert o_data["subtotal"] == 120.0
    assert len(o_data["items"]) == 6

@pytest.mark.asyncio
async def test_prevent_duplicate_borrow_past_orders_and_manual_history(async_client, admin_auth_headers):
    today = date.today()
    unique_ts = time.time_ns()

    # 1. Create Subscription
    sub_res = await async_client.post("/api/admin/subscriptions", json={
        "name": f"Sub Plan {unique_ts}",
        "duration_days": 30,
        "price": 100.0,
        "is_active": True
    }, headers=admin_auth_headers)
    sub_id = sub_res.json()["subscription_id"]

    # 2. Create Two Books
    b1_res = await async_client.post("/api/admin/books", json={
        "serial_number": f"SN-PREV-1-{unique_ts}",
        "title": "History Book One",
        "author": "Author A",
        "price": 200.0,
        "category": "History",
        "language": "English",
        "publish_on_website": True
    }, headers=admin_auth_headers)
    book1_id = b1_res.json()["book_id"]

    b2_res = await async_client.post("/api/admin/books", json={
        "serial_number": f"SN-PREV-2-{unique_ts}",
        "title": "History Book Two",
        "author": "Author B",
        "price": 300.0,
        "category": "History",
        "language": "English",
        "publish_on_website": True
    }, headers=admin_auth_headers)
    book2_id = b2_res.json()["book_id"]

    # 3. Create Member with Book 1 already recorded in past_books
    mem_res = await async_client.post("/api/admin/members", json={
        "name": "Past Books Member",
        "phone": "+91 97777 66666",
        "email": f"pastmember_{unique_ts}@example.com",
        "subscription_type_id": sub_id,
        "subscription_start_date": today.isoformat(),
        "subscription_end_date": (today + timedelta(days=30)).isoformat(),
        "past_books": [{"book_id": book1_id, "title": "History Book One", "date_borrowed": "2024-01-01"}],
        "status": "active"
    }, headers=admin_auth_headers)
    assert mem_res.status_code == 201
    member_id = mem_res.json()["member_id"]

    # 4. Attempting to borrow Book 1 should fail because it was in past_books!
    failed_order_1 = await async_client.post("/api/admin/orders", json={
        "member_id": member_id,
        "book_ids": [book1_id],
        "borrowed_date": today.isoformat(),
        "due_date": (today + timedelta(days=7)).isoformat(),
        "amount_paid": 24.0
    }, headers=admin_auth_headers)
    assert failed_order_1.status_code == 400
    assert "already borrowed" in failed_order_1.json()["detail"]

    # 5. Borrowing Book 2 should succeed!
    success_order = await async_client.post("/api/admin/orders", json={
        "member_id": member_id,
        "book_ids": [book2_id],
        "borrowed_date": today.isoformat(),
        "due_date": (today + timedelta(days=7)).isoformat(),
        "amount_paid": 36.0
    }, headers=admin_auth_headers)
    assert success_order.status_code == 201
    order_id = success_order.json()["order_id"]

    # 6. Return Book 2 so its status is available again
    ret_res = await async_client.post(f"/api/admin/orders/{order_id}/return", json={}, headers=admin_auth_headers)
    assert ret_res.status_code == 200

    # 7. Now attempt to borrow Book 2 AGAIN in a new order -> must fail because member already took Book 2 previously!
    failed_order_2 = await async_client.post("/api/admin/orders", json={
        "member_id": member_id,
        "book_ids": [book2_id],
        "borrowed_date": today.isoformat(),
        "due_date": (today + timedelta(days=7)).isoformat(),
        "amount_paid": 36.0
    }, headers=admin_auth_headers)
    assert failed_order_2.status_code == 400
    assert "already borrowed" in failed_order_2.json()["detail"]

    # 8. Test get previously borrowed books API
    prev_res = await async_client.get(f"/api/admin/members/{member_id}/previously-borrowed-books", headers=admin_auth_headers)
    assert prev_res.status_code == 200
    prev_data = prev_res.json()
    assert book1_id in prev_data["book_ids"]
    assert book2_id in prev_data["book_ids"]
    assert prev_data["total_borrowed_unique_books"] == 2

