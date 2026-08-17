import pytest
from datetime import date, timedelta

@pytest.mark.asyncio
async def test_subscription_and_member_flow(async_client, admin_auth_headers):
    # 1. Create Subscription Plan
    sub_payload = {
        "name": "Standard Monthly",
        "description": "Basic 30-day access",
        "duration_days": 30,
        "price": 150.0,
        "is_active": True
    }
    sub_res = await async_client.post("/api/admin/subscriptions", json=sub_payload, headers=admin_auth_headers)
    assert sub_res.status_code == 201
    sub_data = sub_res.json()
    assert sub_data["subscription_id"] == "SUB-00001"

    # 2. Create Member linked to SUB-00001
    today = date.today()
    mem_payload = {
        "name": "Ravi Kumar",
        "phone": "+91 9876543210",
        "email": "ravi.kumar@example.com",
        "subscription_type_id": "SUB-00001",
        "subscription_start_date": today.isoformat(),
        "subscription_end_date": (today + timedelta(days=30)).isoformat(),
        "status": "active"
    }
    mem_res = await async_client.post("/api/admin/members", json=mem_payload, headers=admin_auth_headers)
    assert mem_res.status_code == 201
    mem_data = mem_res.json()
    assert mem_data["member_id"] == "MEM-00001"
    assert mem_data["email"] == "ravi.kumar@example.com"
