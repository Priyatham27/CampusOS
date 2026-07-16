import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError
from beanie import PydanticObjectId

from app.models.identity.user import (
    User,
    Profile,
    StudentProfile,
    FacultyProfile,
    AdminProfile,
    UserStatus,
    AccountType,
    StudentStatus,
    FacultyStatus
)
from app.models.identity.rbac import (
    Role,
    Permission,
    UserRole,
    RolePermission
)
from app.models.identity.session import (
    Device,
    Session,
    RefreshToken,
    OAuthAccount
)
from app.models.identity.security import (
    PasswordResetToken,
    EmailVerificationToken,
    LoginHistory,
    SecurityEvent,
    SecurityEventType,
    SecurityEventSeverity,
    LoginStatus
)
from app.models.identity.api_key import (
    APIKey
)

pytestmark = pytest.mark.asyncio

async def test_user_validation_success():
    # Verify a valid user is initialized correctly
    org_id = PydanticObjectId()
    user = User(
        userId="USR_123456",
        organizationId=org_id,
        username="john.doe",
        email="john@avanthi.edu",
        status=UserStatus.ACTIVE,
        accountType=AccountType.STUDENT,
        emailVerified=True
    )
    assert user.user_id == "USR_123456"
    assert user.username == "john.doe"
    assert user.email == "john@avanthi.edu"
    assert user.is_deleted is False

async def test_user_validation_failures():
    # Verify username length and format constraints
    org_id = PydanticObjectId()
    
    with pytest.raises(ValidationError):
        # Invalid prefix for user ID
        User(
            userId="INVALID_123456",
            organizationId=org_id,
            username="john.doe",
            email="john@avanthi.edu"
        )

    with pytest.raises(ValidationError):
        # Invalid email format
        User(
            userId="USR_123456",
            organizationId=org_id,
            username="john.doe",
            email="not-an-email"
        )

    with pytest.raises(ValidationError):
        # Invalid username characters
        User(
            userId="USR_123456",
            organizationId=org_id,
            username="john@doe!",
            email="john@avanthi.edu"
        )

async def test_profile_validation_success():
    user_obj_id = PydanticObjectId()
    profile = Profile(
        profileId="PRF_987654",
        userId=user_obj_id,
        firstName="John",
        lastName="Doe",
        phone="+91 98765 43210",
        timezone="Asia/Kolkata",
        language="en"
    )
    assert profile.profile_id == "PRF_987654"
    assert profile.timezone == "Asia/Kolkata"
    assert profile.first_name == "John"

async def test_profile_validation_failures():
    user_obj_id = PydanticObjectId()
    with pytest.raises(ValidationError):
        # Invalid IANA timezone
        Profile(
            profileId="PRF_987654",
            userId=user_obj_id,
            firstName="John",
            lastName="Doe",
            timezone="Invalid/Timezone"
        )

    with pytest.raises(ValidationError):
        # Invalid Phone format
        Profile(
            profileId="PRF_987654",
            userId=user_obj_id,
            firstName="John",
            lastName="Doe",
            phone="123"
        )

async def test_student_profile_academic_separation():
    user_obj_id = PydanticObjectId()
    org_obj_id = PydanticObjectId()
    dept_id = PydanticObjectId()
    prog_id = PydanticObjectId()
    branch_id = PydanticObjectId()
    sem_id = PydanticObjectId()
    sec_id = PydanticObjectId()

    # Valid Student Profile creation (representing academic affiliation)
    student = StudentProfile(
        studentProfileId="STD_111222",
        userId=user_obj_id,
        organizationId=org_obj_id,
        rollNumber="26AVD01",
        departmentId=dept_id,
        programId=prog_id,
        branchId=branch_id,
        semesterId=sem_id,
        sectionId=sec_id,
        batch="2026-2030",
        admissionYear=2026,
        graduationYear=2030,
        studentStatus=StudentStatus.ACTIVE
    )
    assert student.roll_number == "26AVD01"
    assert student.admission_year == 2026
    assert student.graduation_year == 2030

    with pytest.raises(ValidationError):
        # Chronologically invalid admission/graduation years
        StudentProfile(
            studentProfileId="STD_111222",
            userId=user_obj_id,
            organizationId=org_obj_id,
            rollNumber="26AVD01",
            departmentId=dept_id,
            programId=prog_id,
            branchId=branch_id,
            semesterId=sem_id,
            sectionId=sec_id,
            batch="2026-2030",
            admissionYear=2030,
            graduationYear=2026
        )

async def test_rbac_models_validation():
    org_id = PydanticObjectId()
    
    # Valid Role
    role = Role(
        roleId="ROL_888888",
        organizationId=org_id,
        name="Platform Administrator",
        slug="platform-admin",
        priority=1
    )
    assert role.slug == "platform-admin"

    # Valid Permission
    permission = Permission(
        permissionId="PRM_777777",
        module="core",
        resource="users",
        action="read",
        slug="users:read",
        description="Ability to view user accounts"
    )
    assert permission.slug == "users:read"

    with pytest.raises(ValidationError):
        # Invalid permission slug format (no colon)
        Permission(
            permissionId="PRM_777777",
            module="core",
            resource="users",
            action="read",
            slug="invalid_slug"
        )

async def test_session_device_and_security_events():
    user_id = PydanticObjectId()
    org_id = PydanticObjectId()
    
    # Valid Device fingerprint
    device = Device(
        deviceId="DEV_222222",
        userId=user_id,
        deviceName="Developer Mac Studio",
        browser="Safari",
        os="macOS",
        platform="AppleSilicon",
        trusted=True
    )
    assert device.device_name == "Developer Mac Studio"

    # Valid Session record
    session = Session(
        sessionId="SES_333333",
        userId=user_id,
        deviceId="DEV_222222",
        ipAddress="192.168.1.50",
        userAgent="Mozilla/5.0 ...",
        expiresAt=datetime.utcnow() + timedelta(days=1)
    )
    assert session.ip_address == "192.168.1.50"

    # Valid Security Event
    evt = SecurityEvent(
        securityEventId="SEC_555555",
        organizationId=org_id,
        userId=user_id,
        type=SecurityEventType.BRUTE_FORCE_ATTEMPT,
        severity=SecurityEventSeverity.HIGH,
        ipAddress="103.20.14.88"
    )
    assert evt.type == SecurityEventType.BRUTE_FORCE_ATTEMPT
    assert evt.severity == SecurityEventSeverity.HIGH

async def test_api_key_future_ready():
    org_id = PydanticObjectId()
    key = APIKey(
        keyId="AKY_111111",
        organizationId=org_id,
        name="Jenkins CI Integration Key",
        keyHash="sha256_hashed_secret_payload_value",
        scopes=["users:read", "settings:write"]
    )
    assert key.key_id == "AKY_111111"
    assert "users:read" in key.scopes
    assert key.revoked is False

async def test_db_lifecycle_integration(repo):
    # Test document insert, fetch, and soft-delete in test DB
    org_id = PydanticObjectId()
    
    # 1. Insert a User document
    user = User(
        userId="USR_999000",
        organizationId=org_id,
        username="test.user.lifecycle",
        email="lifecycle@avanthi.edu"
    )
    inserted = await user.insert()
    assert inserted.id is not None

    # 2. Query Beanie ODM
    fetched = await User.find_one(User.user_id == "USR_999000")
    assert fetched is not None
    assert fetched.username == "test.user.lifecycle"

    # 3. Soft Delete
    await fetched.soft_delete(reason="Testing lifecycle soft-delete")
    
    # 4. Confirm filtered by default Beanie query expression is_deleted == False
    active = await User.find_one(User.user_id == "USR_999000", User.is_deleted == False)
    assert active is None

    # 5. Verify direct MongoDB collection has it with isDeleted=True
    raw = await User.get_pymongo_collection().find_one({"userId": "USR_999000"})
    assert raw is not None
    assert raw["isDeleted"] is True
    assert raw["changeReason"] == "Testing lifecycle soft-delete"
