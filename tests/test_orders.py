import pytest
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

    # 2. Create Member
    today = date.today()
    mem_payload = {
        "name": "Order Test Member",
        "phone": "+91 99999 88888",
        "email": "ordertest@example.com",
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
        "book_ids": [book_id],
        "borrowed_date": b_date,
        "due_date": d_date,
        "amount_paid": 250.0
    }
    o_res = await async_client.post("/api/admin/orders", json=order_payload, headers=admin_auth_headers)
    assert o_res.status_code == 201
    order_data = o_res.json()
    order_id = order_data["order_id"]
    assert order_data["subtotal"] == 250.0
    assert order_data["items"][0]["price"] == 250.0

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
    assert fetched_order["subtotal"] == 250.0
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
