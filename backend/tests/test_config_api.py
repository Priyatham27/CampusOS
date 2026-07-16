import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

async def test_config_api_integration(async_client: AsyncClient):
    # 1. Create Organization
    org_payload = {
        "organizationId": "ORG_555666",
        "name": "API Config College",
        "shortName": "APICFG",
        "emailDomain": "apicfg.edu",
        "contactEmail": "admin@apicfg.edu"
    }
    await async_client.post("/api/v1/organizations", json=org_payload)

    # 2. POST Create System Config
    sys_payload = {
        "organizationId": None,
        "key": "app.branding.primary_color",
        "value": "#1A73E8",
        "type": "string",
        "scope": "SYSTEM",
        "environment": "PRODUCTION"
    }
    res_sys = await async_client.post("/api/v1/runtime/config", json=sys_payload)
    assert res_sys.status_code == 201
    assert res_sys.json()["data"]["value"] == "#1A73E8"

    # 3. POST Create Organization override
    org_payload = {
        "organizationId": "ORG_555666",
        "key": "app.branding.primary_color",
        "value": "#D93025",
        "type": "string",
        "scope": "ORGANIZATION",
        "environment": "PRODUCTION"
    }
    res_org = await async_client.post("/api/v1/runtime/config", json=org_payload)
    assert res_org.status_code == 201

    # 4. Resolve Configuration hierarchically via API (no user/module context -> returns Org level)
    res_resolve1 = await async_client.get("/api/v1/runtime/config?organizationId=ORG_555666&key=app.branding.primary_color&resolve=true")
    assert res_resolve1.status_code == 200
    assert res_resolve1.json()["data"]["value"] == "#D93025"
    assert res_resolve1.json()["data"]["scope"] == "ORGANIZATION"

    # 5. GET single config by key
    res_get = await async_client.get("/api/v1/runtime/config/app.branding.primary_color?organizationId=ORG_555666")
    assert res_get.status_code == 200
    assert res_get.json()["data"]["value"] == "#D93025"

    # 6. PATCH Update Config
    res_patch = await async_client.patch(
        "/api/v1/runtime/config/app.branding.primary_color?organizationId=ORG_555666",
        json={"value": "#FF0000"}
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["data"]["value"] == "#FF0000"

    # 7. DELETE Config
    res_del = await async_client.delete("/api/v1/runtime/config/app.branding.primary_color?organizationId=ORG_555666")
    assert res_del.status_code == 200
    assert res_del.json()["data"] is True

    # Get resolved after delete: should fall back to SYSTEM level "#1A73E8"
    res_resolve2 = await async_client.get("/api/v1/runtime/config?organizationId=ORG_555666&key=app.branding.primary_color&resolve=true")
    assert res_resolve2.status_code == 200
    assert res_resolve2.json()["data"]["value"] == "#1A73E8"
    assert res_resolve2.json()["data"]["scope"] == "SYSTEM"

    # 8. Create Feature Flag
    flg_payload = {
        "organizationId": "ORG_555666",
        "key": "attendance.qr_scanner",
        "name": "QR Scanner Attendance",
        "category": "Attendance",
        "enabled": False,
        "defaultValue": False,
        "rolloutPercentage": 100,
        "allowedRoles": ["FACULTY"]
    }
    res_flg = await async_client.post("/api/v1/runtime/features", json=flg_payload)
    assert res_flg.status_code == 201

    # 9. Evaluate: False when disabled
    ctx_payload = {
        "userId": "USR_0001",
        "role": "FACULTY",
        "environment": "PRODUCTION"
    }
    res_eval1 = await async_client.post("/api/v1/runtime/features/attendance.qr_scanner/evaluate?organizationId=ORG_555666", json=ctx_payload)
    assert res_eval1.status_code == 200
    assert res_eval1.json()["data"] is False

    # 10. Enable Feature Flag
    res_enable = await async_client.post("/api/v1/runtime/features/attendance.qr_scanner/enable?organizationId=ORG_555666")
    assert res_enable.status_code == 200
    assert res_enable.json()["data"]["enabled"] is True

    # 11. Evaluate: True when enabled and matching role FACULTY
    res_eval2 = await async_client.post("/api/v1/runtime/features/attendance.qr_scanner/evaluate?organizationId=ORG_555666", json=ctx_payload)
    assert res_eval2.status_code == 200
    assert res_eval2.json()["data"] is True

    # Evaluate: False when role is STUDENT
    res_eval3 = await async_client.post(
        "/api/v1/runtime/features/attendance.qr_scanner/evaluate?organizationId=ORG_555666",
        json={"userId": "USR_0001", "role": "STUDENT", "environment": "PRODUCTION"}
    )
    assert res_eval3.status_code == 200
    assert res_eval3.json()["data"] is False

    # 12. Disable Feature Flag
    res_disable = await async_client.post("/api/v1/runtime/features/attendance.qr_scanner/disable?organizationId=ORG_555666")
    assert res_disable.status_code == 200
    assert res_disable.json()["data"]["enabled"] is False
