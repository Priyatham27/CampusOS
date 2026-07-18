import pytest
from datetime import datetime
from unittest.mock import MagicMock
from beanie import PydanticObjectId

from app.main import app
from app.core.identity_context import get_current_identity, IdentityContext
from app.models.org_engine.organization import Organization, OrganizationStatus
from app.models.identity.user import User, UserStatus
from app.models.org_engine.academic import AcademicYear, Semester, Department, Branch, Section
from app.models.org_engine.curriculum import Program, Course
from app.models.calendar import AcademicCalendar
from app.academic.resolver import AcademicResolver
from app.academic.validation import AcademicValidationPipeline
from app.academic.bootstrap import AcademicBootstrapService
from app.academic.exceptions import AcademicHierarchyViolation
from app.academic.metrics import AcademicMetricsService
from app.academic.cache import AcademicCacheLayer
from app.academic.event_publisher import AcademicEventPublisher

pytestmark = pytest.mark.asyncio

# Setup admin role identity override for readiness API routes testing
@pytest.fixture(autouse=True)
def override_identity_dependency_readiness():
    mock_user = MagicMock(spec=User)
    mock_user.id = PydanticObjectId()
    mock_user.user_id = "USR_READINTEST"
    mock_user.status = UserStatus.ACTIVE
    mock_user.profile_id = None
    mock_user.organization_id = PydanticObjectId()

    from app.models.identity.session import Session
    from datetime import timedelta
    mock_session = MagicMock(spec=Session)
    mock_session.session_id = "SES_READINTEST"
    mock_session.device_id = None
    mock_session.expires_at = datetime.utcnow() + timedelta(days=1)

    mock_org = MagicMock(spec=Organization)
    mock_org.id = PydanticObjectId()
    mock_org.status = OrganizationStatus.ACTIVE
    mock_org.timezone = "UTC"

    mock_context = IdentityContext(
        user=mock_user,
        organization=mock_org,
        activeSession=mock_session,
        activeRoles=["SuperAdmin", "admin"],
        permissions=["academic:read", "academic:write"],
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


async def test_academic_resolver_and_caching():
    # 1. Seed org
    org_id = PydanticObjectId()

    # 2. Seed Calendar
    cal = AcademicCalendar(
        calendarId="CAL_000001",
        organization_id=org_id,
        name="Integration Test Calendar",
        timezone="UTC",
        is_active=True,
        weeklyWorkingDays=[0, 1, 2, 3, 4]
    )
    await cal.insert()

    # 3. Seed Academic Year
    from datetime import timedelta
    ay = AcademicYear(
        academicYearId="ACY_000001",
        organization_id=org_id,
        name="Test Year 2026",
        startDate=datetime.utcnow(),
        endDate=datetime.utcnow() + timedelta(days=365),
    )
    await ay.insert()

    # 4. Seed Semester
    sem = Semester(
        semesterId="SEM_000001",
        organization_id=org_id,
        academicYearId=ay.id,
        number=1,
        name="Semester I"
    )
    await sem.insert()

    # 5. Resolve via AcademicResolver
    resolver = AcademicResolver()
    headers = {
        "x-academic-year-id": "ACY_000001",
        "X-Semester-ID": "SEM_000001"
    }
    
    # First query (Cache Miss)
    context1 = await resolver.resolve_academic_context(org_id, headers)
    assert context1.active_calendar is not None
    assert context1.active_calendar.calendar_id == "CAL_000001"
    assert context1.academic_year is not None
    assert context1.academic_year.name == "Test Year 2026"
    assert context1.semester is not None
    assert context1.semester.name == "Semester I"

    # Second query (Cache Hit)
    context2 = await resolver.resolve_academic_context(org_id, headers)
    assert context2.academic_year.id == context1.academic_year.id


async def test_academic_validation_pipeline():
    org_id = PydanticObjectId()
    other_org_id = PydanticObjectId()

    # Create Department
    dept = Department(
        departmentId="DEP_000001",
        organization_id=org_id,
        name="Computer Science",
        code="CS"
    )
    await dept.insert()

    # Create Program (CS)
    prog = Program(
        programId="PRG_000001",
        organization_id=org_id,
        department_id=dept.id,
        name="B.Tech Computer Science",
        duration=4
    )
    await prog.insert()

    # Create Program for other org
    other_prog = Program(
        programId="PRG_000002",
        organization_id=other_org_id,
        department_id=dept.id,
        name="B.Tech Other Org",
        duration=4
    )
    await other_prog.insert()

    # 1. Valid checks
    is_valid = await AcademicValidationPipeline.validate_academic_hierarchy(
        org_id=org_id,
        department_id=dept.id,
        program_id=prog.id
    )
    assert is_valid is True

    # 2. Invalid Org check
    with pytest.raises(AcademicHierarchyViolation) as exc_info:
        await AcademicValidationPipeline.validate_academic_hierarchy(
            org_id=org_id,
            program_id=other_prog.id
        )
    assert "Program does not belong to this organization" in str(exc_info.value)

    # 3. Invalid Program/Dept mismatch check
    other_dept = Department(
        departmentId="DEP_000002",
        organization_id=org_id,
        name="Electrical Engineering",
        code="EE"
    )
    await other_dept.insert()
    
    with pytest.raises(AcademicHierarchyViolation) as exc_info:
        await AcademicValidationPipeline.validate_academic_hierarchy(
            org_id=org_id,
            department_id=other_dept.id,
            program_id=prog.id
        )
    assert "Program does not belong to the specified Department" in str(exc_info.value)


async def test_bootstrap_readiness():
    # Execute bootstrap checks
    await AcademicBootstrapService.bootstrap()


async def test_event_publisher_logs():
    org_id = PydanticObjectId()
    await AcademicEventPublisher.publish_event(
        org_id=org_id,
        event_type="test.event",
        payload={"message": "automated integrations test verification"}
    )


async def test_academic_readiness_routes(async_client):
    org_id = PydanticObjectId()
    # 1. Seed active calendar for health checks query
    cal = AcademicCalendar(
        calendarId="CAL_000002",
        organization_id=org_id,
        name="Health Test Calendar",
        timezone="UTC",
        is_active=True,
        weeklyWorkingDays=[0, 1, 2, 3, 4]
    )
    await cal.insert()

    # 2. Query Health Diagnostics API
    resp = await async_client.get(f"/api/v1/organizations/{org_id}/academic/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["status"] in ["healthy", "degraded"]
    assert "calendar_engine" in data["data"]["components"]

    # 3. Query Performance Metrics API
    resp_metrics = await async_client.get(f"/api/v1/organizations/{org_id}/academic/metrics")
    assert resp_metrics.status_code == 200
    metrics_data = resp_metrics.json()
    assert metrics_data["success"] is True
    assert "resolutionsCount" in metrics_data["data"]
    assert "cacheHits" in metrics_data["data"]
