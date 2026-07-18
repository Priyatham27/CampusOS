import pytest
from datetime import datetime, timedelta
from beanie import PydanticObjectId
from unittest.mock import MagicMock

from app.main import app
from app.core.identity_context import get_current_identity, IdentityContext
from app.models.identity.user import User, UserStatus
from app.models.org_engine.organization import Organization, OrganizationStatus
from app.models.identity.session import Session

pytestmark = pytest.mark.asyncio

@pytest.fixture(autouse=True)
def override_identity_dependency():
    mock_user = MagicMock(spec=User)
    mock_user.id = PydanticObjectId()
    mock_user.user_id = "USR_TESTADMIN"
    mock_user.status = UserStatus.ACTIVE
    mock_user.profile_id = None
    mock_user.organization_id = PydanticObjectId()

    mock_org = MagicMock(spec=Organization)
    mock_org.id = PydanticObjectId()
    mock_org.status = OrganizationStatus.ACTIVE
    mock_org.timezone = "UTC"

    mock_session = MagicMock(spec=Session)
    mock_session.session_id = "SES_TESTADMIN"
    mock_session.device_id = None
    mock_session.expires_at = datetime.utcnow() + timedelta(days=1)

    mock_context = IdentityContext(
        user=mock_user,
        organization=mock_org,
        activeSession=mock_session,
        activeRoles=["SuperAdmin", "admin"],
        permissions=["academic:write", "academic:delete", "department:write", "department:delete"],
        capabilities=[],
        locale="en",
        timezone="UTC",
        featureFlags={},
    )

    async def _mock_identity():
        return mock_context

    app.dependency_overrides[get_current_identity] = _mock_identity
    yield
    if get_current_identity in app.dependency_overrides:
        del app.dependency_overrides[get_current_identity]


async def test_calendar_api_routes(async_client):
    # 1. Create Organization
    org_payload = {
        "organizationId": "ORG_999222",
        "name": "API Calendar College",
        "shortName": "APICAL",
        "emailDomain": "apical.edu",
        "contactEmail": "admin@apical.edu"
    }
    await async_client.post("/api/v1/organizations", json=org_payload)

    # 2. Post Calendar
    cal_payload = {
        "name": "Primary Academic Calendar",
        "timezone": "UTC",
        "weeklyWorkingDays": [0, 1, 2, 3, 4]
    }
    res_post = await async_client.post("/api/v1/organizations/ORG_999222/calendars", json=cal_payload)
    assert res_post.status_code == 200
    data = res_post.json()["data"]
    assert data["name"] == "Primary Academic Calendar"
    cal_id = data["calendarId"]

    # 3. List
    res_list = await async_client.get("/api/v1/organizations/ORG_999222/calendars")
    assert res_list.status_code == 200
    assert len(res_list.json()["data"]) == 1

    # 4. Activate Calendar
    res_act = await async_client.post(f"/api/v1/organizations/ORG_999222/calendars/{cal_id}/activate")
    assert res_act.status_code == 200
    assert res_act.json()["data"]["isActive"] is True

    # 5. Create Holiday
    hol_payload = {
        "calendarId": cal_id,
        "name": "Christmas Break",
        "date": "2026-12-25T00:00:00",
        "type": "PUBLIC",
        "description": "Christmas Break institutional holiday"
    }
    res_hol = await async_client.post("/api/v1/organizations/ORG_999222/holidays", json=hol_payload)
    assert res_hol.status_code == 200
    assert res_hol.json()["data"]["name"] == "Christmas Break"
    hol_id = res_hol.json()["data"]["holidayId"]

    # 6. Create Custom Window
    win_payload = {
        "calendarId": cal_id,
        "windowType": "REGISTRATION",
        "activityType": "EVENTS",
        "name": "Event Registration Open Window",
        "startDate": "2026-06-01T00:00:00",
        "endDate": "2026-06-15T00:00:00",
        "isActive": True
    }
    res_win = await async_client.post("/api/v1/organizations/ORG_999222/scheduling-windows", json=win_payload)
    assert res_win.status_code == 200
    assert res_win.json()["data"]["name"] == "Event Registration Open Window"
    win_id = res_win.json()["data"]["windowId"]

    # 7. Check Active Windows validator
    res_check = await async_client.get(
        "/api/v1/organizations/ORG_999222/timeline/check-window",
        params={
            "windowType": "REGISTRATION",
            "activityType": "EVENTS",
            "checkDate": "2026-06-10T12:00:00"
        }
    )
    assert res_check.status_code == 200
    assert res_check.json()["data"] is True

    # 8. Unified timeline fetching
    res_timeline = await async_client.get("/api/v1/organizations/ORG_999222/timeline")
    assert res_timeline.status_code == 200
    assert res_timeline.json()["data"]["activeCalendar"]["name"] == "Primary Academic Calendar"
    assert len(res_timeline.json()["data"]["holidays"]) == 1

    # 9. Export timeline ICS format
    res_ics = await async_client.get("/api/v1/organizations/ORG_999222/timeline/export")
    assert res_ics.status_code == 200
    assert "text/calendar" in res_ics.headers["content-type"]
    assert "BEGIN:VCALENDAR" in res_ics.text

    # 10. Clean up / Delete Window
    res_del_win = await async_client.delete(f"/api/v1/organizations/ORG_999222/scheduling-windows/{win_id}")
    assert res_del_win.status_code == 200
