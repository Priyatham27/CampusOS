import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

async def test_capability_api_integration(async_client: AsyncClient):
    # 1. Create Organization
    org_payload = {
        "organizationId": "ORG_777000",
        "name": "API Capability College",
        "shortName": "APICAP",
        "emailDomain": "apicap.edu",
        "contactEmail": "admin@apicap.edu"
    }
    await async_client.post("/api/v1/organizations", json=org_payload)

    # 2. Seed Capabilities
    res_seed = await async_client.post("/api/v1/capabilities/seed?organizationId=ORG_777000")
    assert res_seed.status_code == 200
    seed_data = res_seed.json()["data"]
    assert len(seed_data) == 20

    # Find the academic capability and standard custom capability
    academic_cap = next(c for c in seed_data if c["slug"] == "academic")
    academic_id = academic_cap["capabilityId"]

    # 3. GET Capability categories
    res_cats = await async_client.get("/api/v1/capabilities/categories")
    assert res_cats.status_code == 200
    assert "Academic" in res_cats.json()["data"]

    # 4. GET list of capabilities (filtered by category=Academic)
    res_list = await async_client.get("/api/v1/capabilities?organizationId=ORG_777000&category=Academic")
    assert res_list.status_code == 200
    list_data = res_list.json()["data"]
    assert len(list_data) >= 1
    assert any(c["slug"] == "academic" for c in list_data)

    # 5. GET single capability by ID
    res_get = await async_client.get(f"/api/v1/capabilities/{academic_id}?organizationId=ORG_777000")
    assert res_get.status_code == 200
    assert res_get.json()["data"]["slug"] == "academic"

    # 6. GET installed list
    res_installed = await async_client.get("/api/v1/capabilities/installed?organizationId=ORG_777000")
    assert res_installed.status_code == 200
    assert len(res_installed.json()["data"]) >= 8 # Core default is 8

    # 7. Create custom capability
    custom_payload = {
        "organizationId": "ORG_777000",
        "name": "Custom Module",
        "slug": "custom-module",
        "displayName": "Custom API Module",
        "dependencies": ["academic"]
    }
    res_create = await async_client.post("/api/v1/capabilities", json=custom_payload)
    assert res_create.status_code == 201
    custom_cap = res_create.json()["data"]
    custom_id = custom_cap["capabilityId"]

    # 8. Enable custom capability
    res_enable = await async_client.post(f"/api/v1/capabilities/{custom_id}/enable?organizationId=ORG_777000")
    assert res_enable.status_code == 200
    assert res_enable.json()["data"]["enabled"] is True

    # 9. GET enabled list
    res_enabled = await async_client.get("/api/v1/capabilities/enabled?organizationId=ORG_777000")
    assert res_enabled.status_code == 200
    enabled_slugs = [c["slug"] for c in res_enabled.json()["data"]]
    assert "custom-module" in enabled_slugs

    # 10. Update Capability
    update_payload = {
        "displayName": "Custom API Module Revised"
    }
    res_update = await async_client.patch(f"/api/v1/capabilities/{custom_id}?organizationId=ORG_777000", json=update_payload)
    assert res_update.status_code == 200
    assert res_update.json()["data"]["displayName"] == "Custom API Module Revised"

    # Immutability Check: Try updating slug
    res_bad_update = await async_client.patch(
        f"/api/v1/capabilities/{custom_id}?organizationId=ORG_777000",
        json={"slug": "hacked-slug"}
    )
    assert res_bad_update.status_code == 422

    # Disable custom capability
    res_disable = await async_client.post(f"/api/v1/capabilities/{custom_id}/disable?organizationId=ORG_777000")
    assert res_disable.status_code == 200
    assert res_disable.json()["data"]["enabled"] is False

    # 11. Soft Delete Capability
    res_delete = await async_client.delete(f"/api/v1/capabilities/{custom_id}?organizationId=ORG_777000")
    assert res_delete.status_code == 200
    assert res_delete.json()["data"] is True

    # Get after delete should return 404
    res_get_deleted = await async_client.get(f"/api/v1/capabilities/{custom_id}?organizationId=ORG_777000")
    assert res_get_deleted.status_code == 404
