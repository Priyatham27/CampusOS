"""
Story 3.1 — Academic Platform: Comprehensive Test Suite
==========================================================
30+ tests covering:
 - Repository layer (CRUD, soft-delete, bulk operations)
 - Service layer (business rules, hierarchy validation, duplicate detection)
 - API layer (CRUD flows, bulk ops, pagination, 404/409/422 error cases)

NOTE: These tests bypass authentication (test client does not enforce JWT)
and exercise the business logic and data layer end-to-end.
"""
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

# ─────────────────────────────────────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────────────────────────────────────

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

ORG_ID = "ORG_031001"
ORG_ID2 = "ORG_031002"  # Second org for isolation tests

ORG_PAYLOAD = {
    "organizationId": ORG_ID,
    "name": "Academic Test University",
    "shortName": "ACTEST",
    "emailDomain": "actest.edu",
    "contactEmail": "admin@actest.edu",
}
ORG_PAYLOAD2 = {
    "organizationId": ORG_ID2,
    "name": "Second Test University",
    "shortName": "SECTEST",
    "emailDomain": "sectest.edu",
    "contactEmail": "admin@sectest.edu",
}


async def setup_org(async_client, payload=None):
    """Helper to create an organization."""
    p = payload or ORG_PAYLOAD
    await async_client.post("/api/v1/organizations", json=p)


async def create_dep(async_client, org_id=ORG_ID, code="CS", name="Computer Science") -> dict:
    """Create a department and return its data dict."""
    res = await async_client.post(
        f"/api/v1/organizations/{org_id}/departments",
        json={"name": name, "code": code},
    )
    assert res.status_code == 200, f"create_dep failed: {res.json()}"
    return res.json()["data"]


async def create_program(async_client, dep_id: str, org_id=ORG_ID) -> dict:
    """Create a program and return its data dict."""
    res = await async_client.post(
        f"/api/v1/organizations/{org_id}/programs",
        json={"departmentId": dep_id, "name": "B.Tech CS", "duration": 4, "level": "UNDERGRADUATE"},
    )
    assert res.status_code == 200, f"create_program failed: {res.json()}"
    return res.json()["data"]


async def create_branch(async_client, dep_id: str, org_id=ORG_ID) -> dict:
    """Create a branch and return its data dict."""
    res = await async_client.post(
        f"/api/v1/organizations/{org_id}/branches",
        json={"departmentId": dep_id, "code": "AIML", "name": "AI & Machine Learning"},
    )
    assert res.status_code == 200, f"create_branch failed: {res.json()}"
    return res.json()["data"]


async def create_semester(async_client, number: int = 1, org_id=ORG_ID) -> dict:
    """Create a semester and return its data dict."""
    res = await async_client.post(
        f"/api/v1/organizations/{org_id}/semesters",
        json={"number": number, "name": f"Semester {number}", "status": "ACTIVE"},
    )
    assert res.status_code == 200, f"create_semester {number} failed: {res.json()}"
    return res.json()["data"]


async def create_section(async_client, branch_id: str, semester_id: str, name="A", org_id=ORG_ID) -> dict:
    """Create a section and return its data dict."""
    res = await async_client.post(
        f"/api/v1/organizations/{org_id}/sections",
        json={"branchId": branch_id, "semesterId": semester_id, "name": name, "strength": 60},
    )
    assert res.status_code == 200, f"create_section failed: {res.json()}"
    return res.json()["data"]


# ─────────────────────────────────────────────────────────────────────────────
# ACADEMIC YEARS
# ─────────────────────────────────────────────────────────────────────────────

async def test_academic_year_full_crud(async_client):
    """Full CRUD lifecycle for Academic Year."""
    await setup_org(async_client)

    # CREATE
    payload = {"name": "2026-2027", "startDate": "2026-06-01T00:00:00", "endDate": "2027-05-31T00:00:00", "current": True}
    res = await async_client.post(f"/api/v1/organizations/{ORG_ID}/academic-years", json=payload)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["name"] == "2026-2027"
    assert data["current"] is True
    acy_id = data["academicYearId"]

    # GET
    res = await async_client.get(f"/api/v1/organizations/{ORG_ID}/academic-years/{acy_id}")
    assert res.status_code == 200
    assert res.json()["data"]["academicYearId"] == acy_id

    # LIST
    res = await async_client.get(f"/api/v1/organizations/{ORG_ID}/academic-years")
    assert res.status_code == 200
    assert res.json()["meta"]["pagination"]["total"] == 1

    # UPDATE
    res = await async_client.patch(
        f"/api/v1/organizations/{ORG_ID}/academic-years/{acy_id}",
        json={"name": "2026-2027 Revised"},
    )
    assert res.status_code == 200
    assert res.json()["data"]["name"] == "2026-2027 Revised"

    # DELETE
    res = await async_client.delete(f"/api/v1/organizations/{ORG_ID}/academic-years/{acy_id}")
    assert res.status_code == 200

    # GET after delete → 404
    res = await async_client.get(f"/api/v1/organizations/{ORG_ID}/academic-years/{acy_id}")
    assert res.status_code == 404


async def test_academic_year_duplicate_name_rejected(async_client):
    """Creating two academic years with the same name must return 409."""
    await setup_org(async_client)
    payload = {"name": "2026-2027", "startDate": "2026-06-01T00:00:00", "endDate": "2027-05-31T00:00:00"}
    await async_client.post(f"/api/v1/organizations/{ORG_ID}/academic-years", json=payload)
    res = await async_client.post(f"/api/v1/organizations/{ORG_ID}/academic-years", json=payload)
    assert res.status_code == 409


async def test_academic_year_only_one_current(async_client):
    """Setting current=True on a second year must unset the first one."""
    await setup_org(async_client)
    p1 = {"name": "2025-2026", "startDate": "2025-06-01T00:00:00", "endDate": "2026-05-31T00:00:00", "current": True}
    p2 = {"name": "2026-2027", "startDate": "2026-06-01T00:00:00", "endDate": "2027-05-31T00:00:00", "current": True}
    await async_client.post(f"/api/v1/organizations/{ORG_ID}/academic-years", json=p1)
    r2 = await async_client.post(f"/api/v1/organizations/{ORG_ID}/academic-years", json=p2)
    assert r2.status_code == 200

    # List — only one should be current
    res = await async_client.get(f"/api/v1/organizations/{ORG_ID}/academic-years?current=true")
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["name"] == "2026-2027"


async def test_academic_year_bulk_create_and_delete(async_client):
    """Bulk create 3 academic years then bulk delete them."""
    await setup_org(async_client)
    payload = [
        {"name": "2025-2026", "startDate": "2025-06-01T00:00:00", "endDate": "2026-05-31T00:00:00"},
        {"name": "2026-2027", "startDate": "2026-06-01T00:00:00", "endDate": "2027-05-31T00:00:00"},
        {"name": "2027-2028", "startDate": "2027-06-01T00:00:00", "endDate": "2028-05-31T00:00:00"},
    ]
    res = await async_client.post(f"/api/v1/organizations/{ORG_ID}/academic-years/bulk", json=payload)
    assert res.status_code == 200
    ids = [d["academicYearId"] for d in res.json()["data"]]
    assert len(ids) == 3

    # Bulk delete
    res = await async_client.request(
        "DELETE", f"/api/v1/organizations/{ORG_ID}/academic-years/bulk", json={"ids": ids}
    )
    assert res.status_code == 200

    # Verify gone
    res = await async_client.get(f"/api/v1/organizations/{ORG_ID}/academic-years")
    assert res.json()["meta"]["pagination"]["total"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# DEPARTMENTS
# ─────────────────────────────────────────────────────────────────────────────

async def test_department_full_crud(async_client):
    """Full CRUD lifecycle for Department."""
    await setup_org(async_client)

    # CREATE
    res = await async_client.post(
        f"/api/v1/organizations/{ORG_ID}/departments",
        json={"name": "Computer Science", "code": "CS", "status": "ACTIVE"},
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["code"] == "CS"
    dep_id = data["departmentId"]

    # GET
    res = await async_client.get(f"/api/v1/organizations/{ORG_ID}/departments/{dep_id}")
    assert res.status_code == 200

    # UPDATE — add HoD
    res = await async_client.patch(
        f"/api/v1/organizations/{ORG_ID}/departments/{dep_id}",
        json={"hod": "Dr. Alan Turing"},
    )
    assert res.status_code == 200
    assert res.json()["data"]["hod"] == "Dr. Alan Turing"

    # DELETE
    res = await async_client.delete(f"/api/v1/organizations/{ORG_ID}/departments/{dep_id}")
    assert res.status_code == 200

    # GET after delete → 404
    res = await async_client.get(f"/api/v1/organizations/{ORG_ID}/departments/{dep_id}")
    assert res.status_code == 404


async def test_department_duplicate_code_rejected(async_client):
    """Duplicate department code in same org must return 409."""
    await setup_org(async_client)
    await async_client.post(f"/api/v1/organizations/{ORG_ID}/departments", json={"name": "CS Dept", "code": "CS"})
    res = await async_client.post(f"/api/v1/organizations/{ORG_ID}/departments", json={"name": "CS Dup", "code": "CS"})
    assert res.status_code == 409


async def test_department_duplicate_code_case_insensitive(async_client):
    """Department code is upper-cased — 'cs' and 'CS' must conflict."""
    await setup_org(async_client)
    await async_client.post(f"/api/v1/organizations/{ORG_ID}/departments", json={"name": "CS Dept", "code": "CS"})
    res = await async_client.post(f"/api/v1/organizations/{ORG_ID}/departments", json={"name": "CS Lower", "code": "cs"})
    assert res.status_code == 409


async def test_department_bulk_lifecycle(async_client):
    """Bulk create → bulk update → bulk delete departments."""
    await setup_org(async_client)
    bulk_payload = [
        {"name": "Electrical Engineering", "code": "EE"},
        {"name": "Mechanical Engineering", "code": "ME"},
        {"name": "Civil Engineering", "code": "CE"},
    ]
    res = await async_client.post(f"/api/v1/organizations/{ORG_ID}/departments/bulk", json=bulk_payload)
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 3
    dep_ids = [d["departmentId"] for d in data]

    # Bulk update — change HOD on first two
    update_payload = [
        {"departmentId": dep_ids[0], "hod": "Dr. Edison"},
        {"departmentId": dep_ids[1], "hod": "Dr. Tesla"},
    ]
    res = await async_client.patch(f"/api/v1/organizations/{ORG_ID}/departments/bulk", json=update_payload)
    assert res.status_code == 200

    # Verify update
    res = await async_client.get(f"/api/v1/organizations/{ORG_ID}/departments/{dep_ids[0]}")
    assert res.json()["data"]["hod"] == "Dr. Edison"

    # Bulk delete all
    res = await async_client.request(
        "DELETE", f"/api/v1/organizations/{ORG_ID}/departments/bulk", json={"ids": dep_ids}
    )
    assert res.status_code == 200

    res = await async_client.get(f"/api/v1/organizations/{ORG_ID}/departments")
    assert res.json()["meta"]["pagination"]["total"] == 0


async def test_department_org_isolation(async_client):
    """A department created in org A is not visible via org B."""
    await setup_org(async_client, ORG_PAYLOAD)
    await setup_org(async_client, ORG_PAYLOAD2)

    # Create dept in org1
    await async_client.post(
        f"/api/v1/organizations/{ORG_ID}/departments",
        json={"name": "Physics", "code": "PHY"},
    )

    # Try to fetch it from org2
    res = await async_client.get(f"/api/v1/organizations/{ORG_ID2}/departments")
    assert res.json()["meta"]["pagination"]["total"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# PROGRAMS
# ─────────────────────────────────────────────────────────────────────────────

async def test_program_full_crud(async_client):
    """Full CRUD lifecycle for Program."""
    await setup_org(async_client)
    dep = await create_dep(async_client)
    dep_id = dep["id"]

    # CREATE
    res = await async_client.post(
        f"/api/v1/organizations/{ORG_ID}/programs",
        json={"departmentId": dep_id, "name": "B.Tech CS", "duration": 4, "level": "UNDERGRADUATE"},
    )
    assert res.status_code == 200
    prg = res.json()["data"]
    prg_id = prg["programId"]

    # GET
    res = await async_client.get(f"/api/v1/organizations/{ORG_ID}/programs/{prg_id}")
    assert res.status_code == 200

    # UPDATE
    res = await async_client.patch(
        f"/api/v1/organizations/{ORG_ID}/programs/{prg_id}",
        json={"duration": 3},
    )
    assert res.status_code == 200
    assert res.json()["data"]["duration"] == 3

    # DELETE
    await async_client.delete(f"/api/v1/organizations/{ORG_ID}/programs/{prg_id}")
    res = await async_client.get(f"/api/v1/organizations/{ORG_ID}/programs/{prg_id}")
    assert res.status_code == 404


async def test_program_invalid_department_rejected(async_client):
    """Creating a program referencing a non-existent department returns 404."""
    await setup_org(async_client)
    fake_id = str(PydanticObjectId())
    res = await async_client.post(
        f"/api/v1/organizations/{ORG_ID}/programs",
        json={"departmentId": fake_id, "name": "Phantom Program", "duration": 4},
    )
    assert res.status_code == 404


async def test_program_bulk_create(async_client):
    """Bulk create programs under two different departments."""
    await setup_org(async_client)
    dep1 = await create_dep(async_client, code="CS2", name="Computer Science 2")
    dep2 = await create_dep(async_client, code="EE2", name="Electrical Engineering 2")

    bulk_payload = [
        {"departmentId": dep1["id"], "name": "B.Tech CS", "duration": 4, "level": "UNDERGRADUATE"},
        {"departmentId": dep2["id"], "name": "B.Tech EE", "duration": 4, "level": "UNDERGRADUATE"},
    ]
    res = await async_client.post(f"/api/v1/organizations/{ORG_ID}/programs/bulk", json=bulk_payload)
    assert res.status_code == 200
    assert len(res.json()["data"]) == 2


# ─────────────────────────────────────────────────────────────────────────────
# SEMESTERS (Sequential Rules)
# ─────────────────────────────────────────────────────────────────────────────

async def test_semester_sequential_creation(async_client):
    """Semesters must be created in order 1, 2, 3..."""
    await setup_org(async_client)
    # Sem 1 — OK
    res = await async_client.post(
        f"/api/v1/organizations/{ORG_ID}/semesters",
        json={"number": 1, "name": "Semester 1", "status": "ACTIVE"},
    )
    assert res.status_code == 200

    # Sem 3 — SKIP 2 → should fail
    res = await async_client.post(
        f"/api/v1/organizations/{ORG_ID}/semesters",
        json={"number": 3, "name": "Semester 3", "status": "ACTIVE"},
    )
    assert res.status_code == 422  # SemesterSequenceViolation


async def test_semester_sequential_deletion_rule(async_client):
    """Only the highest semester can be soft deleted."""
    await setup_org(async_client)
    s1 = await create_semester(async_client, 1)
    s2 = await create_semester(async_client, 2)

    # Try to delete sem 1 while sem 2 exists — should fail
    res = await async_client.delete(f"/api/v1/organizations/{ORG_ID}/semesters/{s1['semesterId']}")
    assert res.status_code == 422

    # Delete sem 2 first — OK
    res = await async_client.delete(f"/api/v1/organizations/{ORG_ID}/semesters/{s2['semesterId']}")
    assert res.status_code == 200

    # Now delete sem 1 — OK
    res = await async_client.delete(f"/api/v1/organizations/{ORG_ID}/semesters/{s1['semesterId']}")
    assert res.status_code == 200


async def test_semester_update_number_rejected(async_client):
    """Updating the semester number directly is forbidden."""
    await setup_org(async_client)
    s = await create_semester(async_client, 1)
    res = await async_client.patch(
        f"/api/v1/organizations/{ORG_ID}/semesters/{s['semesterId']}",
        json={"number": 5},
    )
    assert res.status_code == 422


async def test_semester_bulk_sequential(async_client):
    """Bulk create 3 semesters in sequential order."""
    await setup_org(async_client)
    payload = [
        {"number": 1, "name": "Semester 1", "status": "ACTIVE"},
        {"number": 2, "name": "Semester 2", "status": "ACTIVE"},
        {"number": 3, "name": "Semester 3", "status": "ACTIVE"},
    ]
    res = await async_client.post(f"/api/v1/organizations/{ORG_ID}/semesters/bulk", json=payload)
    assert res.status_code == 200
    assert len(res.json()["data"]) == 3


# ─────────────────────────────────────────────────────────────────────────────
# BRANCHES
# ─────────────────────────────────────────────────────────────────────────────

async def test_branch_full_crud(async_client):
    """Full CRUD lifecycle for Branch."""
    await setup_org(async_client)
    dep = await create_dep(async_client)
    dep_id = dep["id"]

    res = await async_client.post(
        f"/api/v1/organizations/{ORG_ID}/branches",
        json={"departmentId": dep_id, "code": "AIML", "name": "AI & Machine Learning"},
    )
    assert res.status_code == 200
    brn = res.json()["data"]
    brn_id = brn["branchId"]

    res = await async_client.patch(
        f"/api/v1/organizations/{ORG_ID}/branches/{brn_id}",
        json={"name": "Artificial Intelligence & ML"},
    )
    assert res.status_code == 200
    assert "Artificial Intelligence" in res.json()["data"]["name"]

    await async_client.delete(f"/api/v1/organizations/{ORG_ID}/branches/{brn_id}")
    res = await async_client.get(f"/api/v1/organizations/{ORG_ID}/branches/{brn_id}")
    assert res.status_code == 404


async def test_branch_duplicate_code_rejected(async_client):
    """Duplicate branch code in same department must return 409."""
    await setup_org(async_client)
    dep = await create_dep(async_client)
    dep_id = dep["id"]
    await async_client.post(
        f"/api/v1/organizations/{ORG_ID}/branches",
        json={"departmentId": dep_id, "code": "AIML", "name": "AI"},
    )
    res = await async_client.post(
        f"/api/v1/organizations/{ORG_ID}/branches",
        json={"departmentId": dep_id, "code": "AIML", "name": "AI Dup"},
    )
    assert res.status_code == 409


# ─────────────────────────────────────────────────────────────────────────────
# SECTIONS
# ─────────────────────────────────────────────────────────────────────────────

async def test_section_full_crud(async_client):
    """Full CRUD lifecycle for Section."""
    await setup_org(async_client)
    dep = await create_dep(async_client)
    brn = await create_branch(async_client, dep_id=dep["id"])
    sem = await create_semester(async_client, 1)
    brn_id = brn["id"]
    sem_id = sem["id"]

    res = await async_client.post(
        f"/api/v1/organizations/{ORG_ID}/sections",
        json={"branchId": brn_id, "semesterId": sem_id, "name": "A", "strength": 60},
    )
    assert res.status_code == 200
    sec = res.json()["data"]
    sec_id = sec["sectionId"]

    res = await async_client.patch(
        f"/api/v1/organizations/{ORG_ID}/sections/{sec_id}",
        json={"strength": 75},
    )
    assert res.status_code == 200
    assert res.json()["data"]["strength"] == 75

    await async_client.delete(f"/api/v1/organizations/{ORG_ID}/sections/{sec_id}")
    res = await async_client.get(f"/api/v1/organizations/{ORG_ID}/sections/{sec_id}")
    assert res.status_code == 404


async def test_section_duplicate_name_rejected(async_client):
    """Duplicate section name for same branch+semester must return 409."""
    await setup_org(async_client)
    dep = await create_dep(async_client)
    brn = await create_branch(async_client, dep_id=dep["id"])
    sem = await create_semester(async_client, 1)
    brn_id = brn["id"]
    sem_id = sem["id"]

    await create_section(async_client, brn_id, sem_id, "A")
    res = await async_client.post(
        f"/api/v1/organizations/{ORG_ID}/sections",
        json={"branchId": brn_id, "semesterId": sem_id, "name": "A", "strength": 60},
    )
    assert res.status_code == 409


async def test_section_invalid_branch_rejected(async_client):
    """Referencing a non-existent branch in section creation returns 404."""
    await setup_org(async_client)
    sem = await create_semester(async_client, 1)
    fake_id = str(PydanticObjectId())
    res = await async_client.post(
        f"/api/v1/organizations/{ORG_ID}/sections",
        json={"branchId": fake_id, "semesterId": sem["id"], "name": "A", "strength": 60},
    )
    assert res.status_code == 404


async def test_section_bulk_create(async_client):
    """Bulk create 3 sections for the same branch+semester."""
    await setup_org(async_client)
    dep = await create_dep(async_client)
    brn = await create_branch(async_client, dep_id=dep["id"])
    sem = await create_semester(async_client, 1)

    bulk_payload = [
        {"branchId": brn["id"], "semesterId": sem["id"], "name": "A", "strength": 60},
        {"branchId": brn["id"], "semesterId": sem["id"], "name": "B", "strength": 60},
        {"branchId": brn["id"], "semesterId": sem["id"], "name": "C", "strength": 60},
    ]
    res = await async_client.post(f"/api/v1/organizations/{ORG_ID}/sections/bulk", json=bulk_payload)
    assert res.status_code == 200
    assert len(res.json()["data"]) == 3


# ─────────────────────────────────────────────────────────────────────────────
# COURSES (with new `name` field)
# ─────────────────────────────────────────────────────────────────────────────

async def test_course_full_crud(async_client):
    """Full CRUD lifecycle for Course, verifying the new `name` field."""
    await setup_org(async_client)
    dep = await create_dep(async_client)
    prg = await create_program(async_client, dep_id=dep["id"])
    prg_id = prg["id"]

    # CREATE — with name field
    res = await async_client.post(
        f"/api/v1/organizations/{ORG_ID}/courses",
        json={
            "programId": prg_id,
            "name": "Introduction to Computer Science",
            "courseCode": "CS101",
            "credits": 3.0,
            "semester": "Semester 1",
        },
    )
    assert res.status_code == 200
    crs = res.json()["data"]
    assert crs["name"] == "Introduction to Computer Science"
    assert crs["courseCode"] == "CS101"
    crs_id = crs["courseId"]

    # GET
    res = await async_client.get(f"/api/v1/organizations/{ORG_ID}/courses/{crs_id}")
    assert res.status_code == 200

    # UPDATE name
    res = await async_client.patch(
        f"/api/v1/organizations/{ORG_ID}/courses/{crs_id}",
        json={"name": "Intro to CS (Revised)"},
    )
    assert res.status_code == 200
    assert res.json()["data"]["name"] == "Intro to CS (Revised)"

    # DELETE
    await async_client.delete(f"/api/v1/organizations/{ORG_ID}/courses/{crs_id}")
    res = await async_client.get(f"/api/v1/organizations/{ORG_ID}/courses/{crs_id}")
    assert res.status_code == 404


async def test_course_code_uniqueness(async_client):
    """Two courses cannot share the same course code in same org."""
    await setup_org(async_client)
    dep = await create_dep(async_client)
    prg = await create_program(async_client, dep_id=dep["id"])
    prg_id = prg["id"]

    payload = {
        "programId": prg_id, "name": "OS", "courseCode": "CS201", "credits": 3.0, "semester": "Semester 2"
    }
    await async_client.post(f"/api/v1/organizations/{ORG_ID}/courses", json=payload)
    payload["name"] = "OS Dup"
    res = await async_client.post(f"/api/v1/organizations/{ORG_ID}/courses", json=payload)
    assert res.status_code == 409


async def test_course_code_case_insensitive_uniqueness(async_client):
    """Course codes are normalized to uppercase — 'cs201' conflicts with 'CS201'."""
    await setup_org(async_client)
    dep = await create_dep(async_client)
    prg = await create_program(async_client, dep_id=dep["id"])
    prg_id = prg["id"]

    await async_client.post(
        f"/api/v1/organizations/{ORG_ID}/courses",
        json={"programId": prg_id, "name": "OS", "courseCode": "CS201", "credits": 3.0, "semester": "S2"},
    )
    res = await async_client.post(
        f"/api/v1/organizations/{ORG_ID}/courses",
        json={"programId": prg_id, "name": "OS Lower", "courseCode": "cs201", "credits": 3.0, "semester": "S2"},
    )
    assert res.status_code == 409


async def test_course_bulk_create(async_client):
    """Bulk create multiple courses."""
    await setup_org(async_client)
    dep = await create_dep(async_client)
    prg = await create_program(async_client, dep_id=dep["id"])
    prg_id = prg["id"]

    bulk_payload = [
        {"programId": prg_id, "name": "Data Structures", "courseCode": "CS301", "credits": 4.0, "semester": "S3"},
        {"programId": prg_id, "name": "Algorithms", "courseCode": "CS302", "credits": 4.0, "semester": "S3"},
        {"programId": prg_id, "name": "DBMS", "courseCode": "CS303", "credits": 3.0, "semester": "S4"},
    ]
    res = await async_client.post(f"/api/v1/organizations/{ORG_ID}/courses/bulk", json=bulk_payload)
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 3
    assert all("name" in c for c in data)  # Verify name field present in response


async def test_course_invalid_program_rejected(async_client):
    """Creating a course with a non-existent program returns 404."""
    await setup_org(async_client)
    fake_id = str(PydanticObjectId())
    res = await async_client.post(
        f"/api/v1/organizations/{ORG_ID}/courses",
        json={"programId": fake_id, "name": "Ghost Course", "courseCode": "GH101", "credits": 3.0, "semester": "S1"},
    )
    assert res.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# PAGINATION
# ─────────────────────────────────────────────────────────────────────────────

async def test_pagination_and_total_count(async_client):
    """List endpoint returns correct pagination metadata."""
    await setup_org(async_client)
    # Create 5 departments
    for i in range(5):
        await async_client.post(
            f"/api/v1/organizations/{ORG_ID}/departments",
            json={"name": f"Department {i}", "code": f"D{i:02d}"},
        )

    # Fetch page 1 with limit 2
    res = await async_client.get(f"/api/v1/organizations/{ORG_ID}/departments?skip=0&limit=2")
    assert res.status_code == 200
    meta = res.json()["meta"]["pagination"]
    assert meta["total"] == 5
    assert len(res.json()["data"]) == 2

    # Fetch page 3 (last page, partial)
    res = await async_client.get(f"/api/v1/organizations/{ORG_ID}/departments?skip=4&limit=2")
    assert res.status_code == 200
    assert len(res.json()["data"]) == 1


# ─────────────────────────────────────────────────────────────────────────────
# CROSS-ENTITY HIERARCHY VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

async def test_full_academic_hierarchy(async_client):
    """Integration test: create a full academic hierarchy end-to-end."""
    await setup_org(async_client)

    # Step 1: Academic Year
    acy = await async_client.post(
        f"/api/v1/organizations/{ORG_ID}/academic-years",
        json={"name": "2026-2027", "startDate": "2026-06-01T00:00:00", "endDate": "2027-05-31T00:00:00", "current": True},
    )
    assert acy.status_code == 200

    # Step 2: Department
    dep = await create_dep(async_client, code="CSE", name="Computer Science & Engineering")

    # Step 3: Program
    prg = await create_program(async_client, dep_id=dep["id"])

    # Step 4: Branch
    brn = await create_branch(async_client, dep_id=dep["id"])

    # Step 5: Semester (linked to AcademicYear)
    acy_data = acy.json()["data"]
    sem_res = await async_client.post(
        f"/api/v1/organizations/{ORG_ID}/semesters",
        json={
            "number": 1,
            "name": "Semester 1 (2026-2027)",
            "status": "ACTIVE",
            "academicYearId": acy_data["academicYearId"],
        },
    )
    assert sem_res.status_code == 200
    sem = sem_res.json()["data"]

    # Step 6: Section
    sec = await create_section(async_client, brn["id"], sem["id"])

    # Step 7: Course
    crs_res = await async_client.post(
        f"/api/v1/organizations/{ORG_ID}/courses",
        json={
            "programId": prg["id"],
            "name": "Introduction to Programming",
            "courseCode": "CS101",
            "credits": 4.0,
            "semester": "Semester 1",
        },
    )
    assert crs_res.status_code == 200

    # Verify all entities exist
    res = await async_client.get(f"/api/v1/organizations/{ORG_ID}/academic-years")
    assert res.json()["meta"]["pagination"]["total"] == 1
    res = await async_client.get(f"/api/v1/organizations/{ORG_ID}/departments")
    assert res.json()["meta"]["pagination"]["total"] == 1
    res = await async_client.get(f"/api/v1/organizations/{ORG_ID}/semesters")
    sem_data = res.json()["data"]
    assert len(sem_data) == 1
    # Verify academicYearId FK is preserved
    assert sem_data[0].get("academicYearId") is not None
