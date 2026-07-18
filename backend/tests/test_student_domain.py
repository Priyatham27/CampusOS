import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from beanie import PydanticObjectId

from app.main import app
from app.core.identity_context import get_current_identity, IdentityContext
from app.models.identity.user import User, UserStatus
from app.models.org_engine.organization import Organization, OrganizationStatus
from app.models.identity.session import Session
from app.models.org_engine.academic import AcademicYear, Semester, Department, Branch, Section
from app.models.org_engine.curriculum import Program
from app.student.models import (
    Student, Guardian, StudentDocument, StudentAchievement, StudentSkill, StudentStatus, SkillLevel
)
from app.student.service import StudentService, ProfileService
from app.student.exceptions import (
    DuplicateRollNumber, StudentArchivedReadOnly, StudentNotFound, GuardianLimitExceeded
)

pytestmark = pytest.mark.asyncio

@pytest.fixture(autouse=True)
def override_identity_dependency_student():
    mock_user = MagicMock(spec=User)
    mock_user.id = PydanticObjectId()
    mock_user.user_id = "USR_STUDENTADMIN"
    mock_user.status = UserStatus.ACTIVE
    mock_user.profile_id = None
    mock_user.organization_id = PydanticObjectId()

    mock_org = MagicMock(spec=Organization)
    mock_org.id = PydanticObjectId()
    mock_org.status = OrganizationStatus.ACTIVE
    mock_org.timezone = "UTC"

    mock_session = MagicMock(spec=Session)
    mock_session.session_id = "SES_STUDENTADMIN"
    mock_session.device_id = None
    mock_session.expires_at = datetime.utcnow() + timedelta(days=1)

    mock_context = IdentityContext(
        user=mock_user,
        organization=mock_org,
        activeSession=mock_session,
        activeRoles=["SuperAdmin", "admin"],
        permissions=["student:read", "student:write", "student:delete"],
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


async def test_student_creation_and_roll_number_uniqueness():
    org_id = PydanticObjectId()
    student_svc = StudentService()

    # 1. Seed Academic Hierarchy
    dept = await Department(
        departmentId="DEP_000010",
        organization_id=org_id,
        name="Electronics",
        code="ECE"
    ).insert()

    prog = await Program(
        programId="PRG_000010",
        organization_id=org_id,
        department_id=dept.id,
        name="B.Tech Electronics",
        duration=4
    ).insert()

    # 2. Valid Student payload
    payload = {
        "rollNumber": "ECE-2026-05",
        "firstName": "John",
        "lastName": "Doe",
        "email": "johndoe@university.edu",
        "phone": "+919876543210",
        "dateOfBirth": datetime(2004, 5, 15),
        "gender": "MALE",
        "departmentId": dept.id,
        "programId": prog.id
    }

    student = await student_svc.create_student(org_id, payload)
    assert student.student_id.startswith("STU_")
    assert student.roll_number == "ECE-2026-05"
    assert student.first_name == "John"
    
    # Verify User was auto-created
    user = await User.find_one(User.email == "johndoe@university.edu")
    assert user is not None
    assert user.account_type == "STUDENT"

    # 3. Create Duplicate Roll Number (Raises error)
    with pytest.raises(DuplicateRollNumber):
        await student_svc.create_student(org_id, payload)


async def test_student_archiving_and_read_only_protection():
    org_id = PydanticObjectId()
    student_svc = StudentService()
    profile_svc = ProfileService()

    # Create Student
    student = Student(
        studentId="STU_999001",
        userId=PydanticObjectId(),
        organization_id=org_id,
        rollNumber="ROLL-999",
        firstName="Archie",
        lastName="Andrews",
        email="archie@school.com",
        dateOfBirth=datetime(2004, 1, 1),
        gender="MALE",
        status=StudentStatus.ACTIVE
    )
    await student.insert()

    # Archive Student
    archived = await student_svc.archive_student("STU_999001", org_id)
    assert archived.is_archived is True
    assert archived.status == StudentStatus.ARCHIVED

    # Try updating archived student -> Should fail
    update_payload = {"firstName": "Archibald"}
    with pytest.raises(StudentArchivedReadOnly):
        await student_svc.update_student("STU_999001", org_id, update_payload)

    # Try adding guardian to archived student -> Should fail
    guardian_payload = {
        "name": "Fred Andrews",
        "relation": "FATHER",
        "phone": "+15550199",
        "isPrimary": True
    }
    with pytest.raises(StudentArchivedReadOnly):
        await profile_svc.add_guardian("STU_999001", org_id, guardian_payload)


async def test_guardians_and_documents_management():
    org_id = PydanticObjectId()
    student_svc = StudentService()
    profile_svc = ProfileService()

    # Create Student
    student = Student(
        studentId="STU_555666",
        userId=PydanticObjectId(),
        organization_id=org_id,
        rollNumber="ROLL-555",
        firstName="Betty",
        lastName="Cooper",
        email="betty@school.com",
        dateOfBirth=datetime(2004, 1, 1),
        gender="FEMALE",
        status=StudentStatus.ACTIVE
    )
    await student.insert()

    # 1. Add Primary Guardian
    g_payload = {
        "name": "Alice Cooper",
        "relation": "MOTHER",
        "phone": "+15550299",
        "isPrimary": True
    }
    guardian = await profile_svc.add_guardian("STU_555666", org_id, g_payload)
    assert guardian.guardian_id.startswith("GUA_")
    assert guardian.is_primary is True

    # 2. Add Second Guardian
    g2_payload = {
        "name": "Hal Cooper",
        "relation": "FATHER",
        "phone": "+15550399",
        "isPrimary": False
    }
    g2 = await profile_svc.add_guardian("STU_555666", org_id, g2_payload)
    assert g2.is_primary is False

    # 3. Add Document
    doc_payload = {
        "name": "High School Transcript",
        "filePath": "s3://campusos/transcripts/betty.pdf",
        "fileType": "PDF",
        "fileSize": 102400,
        "category": "ACADEMIC"
    }
    doc = await profile_svc.add_document("STU_555666", org_id, doc_payload)
    assert doc.document_id.startswith("DOC_")
    assert doc.is_verified is False

    # Verify Document
    verified_doc = await profile_svc.verify_document(doc.document_id, "STU_555666", org_id, True)
    assert verified_doc.is_verified is True


async def test_skills_and_achievements_logging():
    org_id = PydanticObjectId()
    profile_svc = ProfileService()

    # Create Student
    student = Student(
        studentId="STU_777888",
        userId=PydanticObjectId(),
        organization_id=org_id,
        rollNumber="ROLL-777",
        firstName="Jughead",
        lastName="Jones",
        email="jughead@school.com",
        dateOfBirth=datetime(2004, 1, 1),
        gender="MALE",
        status=StudentStatus.ACTIVE
    )
    await student.insert()

    # 1. Add Skill
    skill = await profile_svc.add_skill("STU_777888", org_id, {"name": "Python", "level": "ADVANCED"})
    assert skill.skill_id.startswith("SKL_")
    assert skill.level == "ADVANCED"

    # 2. Add Achievement
    ach = await profile_svc.add_achievement("STU_777888", org_id, {
        "title": "State Writing Competition First Prize",
        "description": "Won first prize in annual creative writing league.",
        "category": "CULTURAL"
    })
    assert ach.achievement_id.startswith("ACH_")
    assert ach.category == "CULTURAL"


async def test_student_directory_api_routes(async_client):
    org_id = PydanticObjectId()
    
    # Create Student
    student = Student(
        studentId="STU_333444",
        userId=PydanticObjectId(),
        organization_id=org_id,
        rollNumber="ROLL-333",
        firstName="Veronica",
        lastName="Lodge",
        email="veronica@lodge.com",
        dateOfBirth=datetime(2004, 1, 1),
        gender="FEMALE",
        status=StudentStatus.ACTIVE
    )
    await student.insert()

    # 1. Test search students route
    resp = await async_client.get(f"/api/v1/organizations/{org_id}/students?searchQuery=Veronica")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert len(data["data"]) == 1
    assert data["data"][0]["firstName"] == "Veronica"

    # 2. Test consolidated profile route
    resp_prof = await async_client.get(f"/api/v1/organizations/{org_id}/students/STU_333444/profile")
    assert resp_prof.status_code == 200
    prof_data = resp_prof.json()
    assert prof_data["success"] is True
    assert prof_data["data"]["student"]["lastName"] == "Lodge"
    assert isinstance(prof_data["data"]["guardians"], list)
