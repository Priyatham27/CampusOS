import pytest

pytestmark = pytest.mark.asyncio

async def test_api_create_organization(async_client):
    payload = {
        "organizationId": "ORG_999111",
        "name": "API College",
        "shortName": "APICol",
        "emailDomain": "apicol.edu",
        "contactEmail": "admin@apicol.edu",
        "timezone": "Asia/Kolkata",
        "country": "India",
        "website": "https://apicol.edu"
    }
    
    response = await async_client.post("/api/v1/organizations", json=payload)
    assert response.status_code == 201
    
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "Organization created successfully."
    assert data["data"]["slug"] == "api-college"
    assert data["data"]["timezone"] == "Asia/Kolkata"

async def test_api_validation_errors(async_client):
    # Invalid ID format and invalid timezone
    payload = {
        "organizationId": "invalid-id",
        "name": "API College",
        "shortName": "APICol",
        "emailDomain": "apicol.edu",
        "contactEmail": "admin@apicol.edu",
        "timezone": "Invalid/Zone"
    }
    response = await async_client.post("/api/v1/organizations", json=payload)
    assert response.status_code == 422
    assert response.json()["success"] is False

async def test_api_fetch_and_update(async_client):
    # Create first
    payload = {
        "organizationId": "ORG_888222",
        "name": "Update College",
        "shortName": "UpCol",
        "emailDomain": "upcol.edu",
        "contactEmail": "admin@upcol.edu"
    }
    await async_client.post("/api/v1/organizations", json=payload)

    # Fetch
    res_get = await async_client.get("/api/v1/organizations/ORG_888222")
    assert res_get.status_code == 200
    assert res_get.json()["data"]["name"] == "Update College"

    # Patch
    patch_payload = {
        "name": "Updated Name College",
        "shortName": "NewShort"
    }
    res_patch = await async_client.patch("/api/v1/organizations/ORG_888222", json=patch_payload)
    assert res_patch.status_code == 200
    assert res_patch.json()["data"]["name"] == "Updated Name College"
    assert res_patch.json()["data"]["shortName"] == "NewShort"

async def test_api_delete_and_list(async_client):
    payload = {
        "organizationId": "ORG_777333",
        "name": "Delete College",
        "shortName": "DelCol",
        "emailDomain": "delcol.edu",
        "contactEmail": "admin@delcol.edu"
    }
    await async_client.post("/api/v1/organizations", json=payload)

    # List checking count
    res_list = await async_client.get("/api/v1/organizations")
    assert len(res_list.json()["data"]) == 1

    # Delete
    res_del = await async_client.delete("/api/v1/organizations/ORG_777333")
    assert res_del.status_code == 204

    # List again - should be empty now
    res_list_post = await async_client.get("/api/v1/organizations")
    assert len(res_list_post.json()["data"]) == 0
