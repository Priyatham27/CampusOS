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

async def test_api_academic_years_crud(async_client):
    # 1. Create Organization
    org_payload = {
        "organizationId": "ORG_999000",
        "name": "API Academic College",
        "shortName": "APIACAD",
        "emailDomain": "apiacad.edu",
        "contactEmail": "admin@apiacad.edu"
    }
    await async_client.post("/api/v1/organizations", json=org_payload)

    # 2. Post Academic Year
    acy_payload = {
        "name": "2026-2027",
        "startDate": "2026-06-01T00:00:00",
        "endDate": "2027-05-31T00:00:00",
        "current": True
    }
    res_post = await async_client.post("/api/v1/organizations/ORG_999000/academic-years", json=acy_payload)
    assert res_post.status_code == 200
    data = res_post.json()["data"]
    assert data["name"] == "2026-2027"
    acy_id = data["academicYearId"]

    # 3. List
    res_list = await async_client.get("/api/v1/organizations/ORG_999000/academic-years")
    assert res_list.status_code == 200
    assert len(res_list.json()["data"]) == 1

    # 4. Get by ID
    res_get = await async_client.get(f"/api/v1/organizations/ORG_999000/academic-years/{acy_id}")
    assert res_get.status_code == 200
    assert res_get.json()["data"]["name"] == "2026-2027"

    # 5. Patch
    res_patch = await async_client.patch(
        f"/api/v1/organizations/ORG_999000/academic-years/{acy_id}",
        json={"name": "2026-2027 Revised"}
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["data"]["name"] == "2026-2027 Revised"

    # 6. Delete
    res_del = await async_client.delete(f"/api/v1/organizations/ORG_999000/academic-years/{acy_id}")
    assert res_del.status_code == 200

    # Get after delete should return 404 (AcademicYearNotFound)
    res_get_deleted = await async_client.get(f"/api/v1/organizations/ORG_999000/academic-years/{acy_id}")
    assert res_get_deleted.status_code == 404


async def test_api_departments_bulk_crud(async_client):
    # 1. Create Organization
    org_payload = {
        "organizationId": "ORG_999111",
        "name": "API Bulk Department College",
        "shortName": "APIDEP",
        "emailDomain": "apidep.edu",
        "contactEmail": "admin@apidep.edu"
    }
    await async_client.post("/api/v1/organizations", json=org_payload)

    # 2. Bulk Post Departments
    bulk_payload = [
        {"name": "Chemical Engineering", "code": "CHEM"},
        {"name": "Civil Engineering", "code": "CIVIL"}
    ]
    res_bulk = await async_client.post("/api/v1/organizations/ORG_999111/departments/bulk", json=bulk_payload)
    assert res_bulk.status_code == 200
    data = res_bulk.json()["data"]
    assert len(data) == 2
    dep_id_1 = data[0]["departmentId"]
    dep_id_2 = data[1]["departmentId"]

    # 3. Bulk Update
    update_payload = [
        {"departmentId": dep_id_1, "name": "Chemical Engineering Revised"},
        {"departmentId": dep_id_2, "hod": "Dr. Marie Curie"}
    ]
    res_update = await async_client.patch("/api/v1/organizations/ORG_999111/departments/bulk", json=update_payload)
    assert res_update.status_code == 200

    # Get department to verify
    res_get = await async_client.get(f"/api/v1/organizations/ORG_999111/departments/{dep_id_1}")
    assert res_get.json()["data"]["name"] == "Chemical Engineering Revised"

    # 4. Bulk Delete
    res_del = await async_client.request(
        "DELETE",
        "/api/v1/organizations/ORG_999111/departments/bulk",
        json={"ids": [dep_id_1, dep_id_2]}
    )
    assert res_del.status_code == 200

    # Check that they are gone
    res_list = await async_client.get("/api/v1/organizations/ORG_999111/departments")
    assert len(res_list.json()["data"]) == 0
