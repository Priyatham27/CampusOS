import pytest
import io
from PIL import Image

pytestmark = pytest.mark.asyncio


async def test_api_branding_lifecycle(async_client):

    # 1. Create Organization first
    org_payload = {
        "organizationId": "ORG_555666",
        "name": "API Branding College",
        "shortName": "APIBrand",
        "emailDomain": "apibrand.edu",
        "contactEmail": "admin@apibrand.edu"
    }
    await async_client.post("/api/v1/organizations", json=org_payload)

    # 2. Get Branding
    res_get = await async_client.get("/api/v1/organizations/ORG_555666/branding")
    assert res_get.status_code == 200
    data = res_get.json()
    assert data["success"] is True
    assert data["data"]["primaryColor"] == "#4F46E5"
    assert "cssVariables" in data["data"]
    assert "tailwindTokens" in data["data"]

    # 3. Patch Branding with preview=True
    patch_payload = {
        "primaryColor": "#ABCDEF",
        "theme": "dark"
    }
    res_patch_preview = await async_client.patch(
        "/api/v1/organizations/ORG_555666/branding?preview=true", 
        json=patch_payload
    )
    assert res_patch_preview.status_code == 200
    assert res_patch_preview.json()["data"]["primaryColor"] == "#ABCDEF"
    assert res_patch_preview.json()["meta"]["previewMode"] is True

    # Active configuration still default
    res_get_active = await async_client.get("/api/v1/organizations/ORG_555666/branding")
    assert res_get_active.json()["data"]["primaryColor"] == "#4F46E5"

    # 4. Patch Branding publish (preview=False)
    res_publish = await async_client.patch(
        "/api/v1/organizations/ORG_555666/branding?preview=false", 
        json=patch_payload
    )
    assert res_publish.status_code == 200
    assert res_publish.json()["data"]["primaryColor"] == "#ABCDEF"
    assert res_publish.json()["data"]["version"] == 2

    # 5. Reset branding
    res_reset = await async_client.post("/api/v1/organizations/ORG_555666/branding/reset")
    assert res_reset.status_code == 200
    assert res_reset.json()["data"]["primaryColor"] == "#4F46E5"
    assert res_reset.json()["data"]["version"] == 3

    # 6. Retrieve History
    res_history = await async_client.get("/api/v1/organizations/ORG_555666/branding/history")
    assert res_history.status_code == 200
    history_list = res_history.json()["data"]
    assert len(history_list) == 2  # one from patch, one from reset
    assert history_list[0]["version"] == 2

    # 7. Rollback to version 2 (with primary_color = #ABCDEF)
    res_rollback = await async_client.post("/api/v1/organizations/ORG_555666/branding/rollback/2")
    assert res_rollback.status_code == 200
    assert res_rollback.json()["data"]["primaryColor"] == "#ABCDEF"
    assert res_rollback.json()["data"]["version"] == 4

async def test_api_logo_upload_and_delete(async_client):
    # Create Org
    org_payload = {
        "organizationId": "ORG_444999",
        "name": "Upload API College",
        "shortName": "UpAPI",
        "emailDomain": "upapi.edu",
        "contactEmail": "admin@upapi.edu"
    }
    await async_client.post("/api/v1/organizations", json=org_payload)

    # 1. Upload Logo
    img = Image.new("RGBA", (64, 64), color="red")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    file_content = img_byte_arr.getvalue()
    
    logo_file = {"file": ("logo.png", io.BytesIO(file_content), "image/png")}

    
    res_logo = await async_client.post(
        "/api/v1/organizations/ORG_444999/branding/logo?isDark=false", 
        files=logo_file
    )
    assert res_logo.status_code == 200
    assert "logo.png" in res_logo.json()["data"]["organizationLogo"]

    # 2. Upload dark logo variant
    dark_logo_file = {"file": ("dark_logo.png", io.BytesIO(file_content), "image/png")}
    res_dark_logo = await async_client.post(
        "/api/v1/organizations/ORG_444999/branding/logo?isDark=true", 
        files=dark_logo_file
    )
    assert res_dark_logo.status_code == 200
    assert "dark_logo.png" in res_dark_logo.json()["data"]["darkLogo"]

    # 3. Soft remove logo variant
    res_del_logo = await async_client.delete("/api/v1/organizations/ORG_444999/branding/logo?isDark=false")
    assert res_del_logo.status_code == 200
    assert res_del_logo.json()["data"]["organizationLogo"] is None
    assert res_del_logo.json()["data"]["darkLogo"] is not None  # Dark logo still remains

async def test_api_invalid_color_validation(async_client):
    # Create Org
    org_payload = {
        "organizationId": "ORG_111333",
        "name": "Val API College",
        "shortName": "ValAPI",
        "emailDomain": "valapi.edu",
        "contactEmail": "admin@valapi.edu"
    }
    await async_client.post("/api/v1/organizations", json=org_payload)

    # Validation check - invalid hex color code format
    res_invalid_color = await async_client.patch(
        "/api/v1/organizations/ORG_111333/branding", 
        json={"primaryColor": "invalid-color-format"}
    )
    assert res_invalid_color.status_code == 422
