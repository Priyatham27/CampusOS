import pytest
import io
import jwt
from datetime import datetime, timedelta
from beanie import PydanticObjectId
from httpx import AsyncClient

from apps.api.app.core.config import settings
from apps.api.app.models.org_engine.organization import Organization
from apps.api.app.models.org_engine.academic import Department, Branch, Semester, Section
from apps.api.app.models.org_engine.curriculum import Program
from apps.api.app.models.identity.user import User, Profile, UserStatus, AccountType, StudentProfile, StudentStatus
from apps.api.app.models.identity.rbac import Role, Permission, UserRole, RolePermission
from apps.api.app.repositories.user import UserRepository
from apps.api.app.repositories.profile import ProfileRepository
from apps.api.app.services.user import UserService
from apps.api.app.services.profile import ProfileService
from apps.api.app.services.user_search import UserSearchService
from apps.api.app.services.bulk_import import BulkImportService
from apps.api.app.services.credential import CredentialService
from apps.api.app.services.authentication import AuthenticationService
from apps.api.app.core.user_exceptions import UserNotFound, DuplicateUsername, DuplicateEmail

pytestmark = pytest.mark.asyncio

async def setup_test_system() -> tuple[Organization, User, str, str]:
    """Helper to provision a tenant organization, roles, permissions, admin user, and return (org, admin_user, token, headers)"""
    # 1. Organization
    org = Organization(
        organizationId="ORG_888888",
        name="Avanthi College",
        shortName="Avanthi",
        slug="avanthi-col",
        emailDomain="avanthi.edu",
        contactEmail="admin@avanthi.edu"
    )
    await org.insert()

    # 2. Permissions
    read_perm = Permission(
        permissionId="PRM_000001",
        module="core",
        resource="users",
        action="read",
        slug="users:read"
    )
    await read_perm.insert()

    manage_perm = Permission(
        permissionId="PRM_000002",
        module="core",
        resource="users",
        action="manage",
        slug="users:manage"
    )
    await manage_perm.insert()

    # 3. Admin Role
    admin_role = Role(
        roleId="ROL_000001",
        organizationId=org.id,
        name="Administrator",
        slug="admin",
        priority=1
    )
    await admin_role.insert()

    # Link Permissions to Admin Role
    await RolePermission(roleId=admin_role.id, permissionId=read_perm.id).insert()
    await RolePermission(roleId=admin_role.id, permissionId=manage_perm.id).insert()

    # 4. Admin User
    admin_user = User(
        userId="USR_000001",
        organizationId=org.id,
        username="admin",
        email="admin@avanthi.edu",
        status=UserStatus.ACTIVE,
        emailVerified=True
    )
    await admin_user.insert()

    # Link Admin User to Admin Role
    await UserRole(userId=admin_user.id, roleId=admin_role.id).insert()

    # Create Password Credential
    cs = CredentialService()
    await cs.create_credential(user_id_str=str(admin_user.id), password="AdminPassword123!")

    # Login to generate token
    as_svc = AuthenticationService()
    payload = {
        "email": "admin@avanthi.edu",
        "password": "AdminPassword123!",
        "provider": "password"
    }
    auth_res = await as_svc.login(
        org_id_str=str(org.id),
        payload=payload,
        user_agent="Pytest Agent",
        ip_address="127.0.0.1"
    )
    
    token = auth_res["accessToken"]
    headers = {
        "Authorization": f"Bearer {token}",
        "x-tenant-slug": org.slug
    }

    return org, admin_user, token, headers

# =====================================================================
# REPOSITORY TESTS
# =====================================================================

async def test_user_profile_repository_flow():
    org = Organization(
        organizationId="ORG_111111",
        name="Test Institution",
        shortName="TestInst",
        slug="test-inst",
        emailDomain="test.edu",
        contactEmail="admin@test.edu"
    )
    await org.insert()

    user_repo = UserRepository()
    profile_repo = ProfileRepository()

    # 1. Create User
    user = User(
        userId="USR_111222",
        organizationId=org.id,
        username="test.user",
        email="test.user@test.edu",
        status=UserStatus.ACTIVE
    )
    saved_user = await user_repo.create(user)
    assert saved_user.id is not None
    assert saved_user.username == "test.user"

    # 2. Create Profile
    profile = Profile(
        profileId="PRF_111222",
        userId=saved_user.id,
        firstName="Test",
        lastName="User"
    )
    saved_profile = await profile_repo.create(profile)
    assert saved_profile.id is not None
    assert saved_profile.user_id == saved_user.id

    # Link Profile back
    saved_user.profile_id = saved_profile.id
    await user_repo.update(saved_user, {"profileId": saved_profile.id})

    # 3. Find Ops
    fetched_user = await user_repo.find_by_id("USR_111222", org.id)
    assert fetched_user is not None
    assert fetched_user.email == "test.user@test.edu"

    fetched_profile = await profile_repo.find_by_user_beanie_id(saved_user.id)
    assert fetched_profile is not None
    assert fetched_profile.first_name == "Test"

    # 4. Soft Delete and Restore
    await user_repo.delete(saved_user)
    assert saved_user.is_deleted is True

    # Find active user should fail
    active_user = await user_repo.find_by_id("USR_111222", org.id)
    assert active_user is None

    # Restore
    await user_repo.restore(saved_user)
    assert saved_user.is_deleted is False
    active_user = await user_repo.find_by_id("USR_111222", org.id)
    assert active_user is not None

# =====================================================================
# SERVICE LAYER TESTS
# =====================================================================

async def test_user_service_lifecycle():
    org, admin_user, token, headers = await setup_test_system()
    us = UserService()

    user_data = {
        "username": "jane.doe",
        "email": "jane@avanthi.edu",
        "first_name": "Jane",
        "last_name": "Doe",
        "password": "Password123!"
    }

    # Create User
    user = await us.create_user(str(org.id), user_data, current_user=admin_user)
    assert user.user_id.startswith("USR_")
    assert user.email == "jane@avanthi.edu"
    assert user.status == UserStatus.ACTIVE

    # Check profile created automatically
    profile = await us.profile_repo.find_by_user_beanie_id(user.id)
    assert profile is not None
    assert profile.first_name == "Jane"
    assert profile.last_name == "Doe"

    # Duplicate check
    with pytest.raises(DuplicateUsername):
        await us.create_user(str(org.id), user_data, current_user=admin_user)

    # Change status
    updated_user = await us.change_user_status(str(org.id), user.user_id, UserStatus.SUSPENDED, current_user=admin_user)
    assert updated_user.status == UserStatus.SUSPENDED

    # Bulk status modification
    bulk_res = await us.bulk_status_change(str(org.id), [user.user_id], UserStatus.ACTIVE, current_user=admin_user)
    assert user.user_id in bulk_res["success"]

# =====================================================================
# SEARCH SERVICE TESTS
# =====================================================================

async def test_user_search_filtration():
    org, admin_user, token, headers = await setup_test_system()
    us = UserService()
    ss = UserSearchService()

    # Create users
    u1 = await us.create_user(str(org.id), {
        "username": "search.one",
        "email": "one@avanthi.edu",
        "first_name": "Kranthi",
        "last_name": "Kumar"
    }, current_user=admin_user)

    u2 = await us.create_user(str(org.id), {
        "username": "search.two",
        "email": "two@avanthi.edu",
        "first_name": "Pratap",
        "last_name": "Rao"
    }, current_user=admin_user)

    # Global text match
    users, total = await ss.search_users(org.id, query_str="Kranthi")
    assert total == 1
    assert users[0].id == u1.id

    # Filter by Account Type
    users, total = await ss.search_users(org.id, filters={"accountType": AccountType.STUDENT})
    # admin, u1, u2 are all STUDENT by default
    assert total == 3

# =====================================================================
# BULK IMPORT TESTS
# =====================================================================

async def test_bulk_import_csv():
    org, admin_user, token, headers = await setup_test_system()
    bulk_svc = BulkImportService()

    # Setup roles and academic entities
    role = Role(
        roleId="ROL_000002",
        organizationId=org.id,
        name="Student",
        slug="student",
        priority=10
    )
    await role.insert()

    dept = Department(
        departmentId="DEP_000001",
        organizationId=org.id,
        name="Computer Science",
        code="CSE",
        status="ACTIVE"
    )
    await dept.insert()

    # CSV data
    csv_data = """username,email,firstName,lastName,accountType,roleSlug,phone,rollNumber,departmentCode,batch,admissionYear,graduationYear
alex.smith,alex@avanthi.edu,Alex,Smith,STUDENT,student,+91 99999 88888,26AVD02,CSE,2026,2026,2030
bob.jones,bob@avanthi.edu,Bob,Jones,STUDENT,student,,26AVD03,CSE,2026,2026,2030
"""

    # Preview Mode
    preview_report = await bulk_svc.import_users_csv(str(org.id), csv_data, preview=True, current_user=admin_user)
    assert preview_report["totalProcessed"] == 2
    assert preview_report["successCount"] == 2
    assert preview_report["failureCount"] == 0
    assert len(preview_report["rows"]) == 2
    assert preview_report["rows"][0]["status"] == "VALID"

    # Actual Ingestion Mode
    import_report = await bulk_svc.import_users_csv(str(org.id), csv_data, preview=False, current_user=admin_user)
    assert import_report["successCount"] == 2

    # Check imported user exists
    user = await User.find_one(User.username == "alex.smith")
    assert user is not None
    assert user.email == "alex@avanthi.edu"

    # Verify student profile generated
    std_prof = await StudentProfile.find_one(StudentProfile.user_id == user.id)
    assert std_prof is not None
    assert std_prof.roll_number == "26AVD02"
    assert std_prof.department_id == dept.id

# =====================================================================
# API CONTROLLER TESTS (FASTAPI ROUTES)
# =====================================================================

async def test_fastapi_endpoints(async_client):
    org, admin_user, token, headers = await setup_test_system()

    # 1. Create User via POST
    payload = {
        "username": "post.user",
        "email": "post@avanthi.edu",
        "accountType": "STUDENT",
        "firstName": "Post",
        "lastName": "User",
        "password": "Password123!"
    }
    response = await async_client.post("/api/v1/users", json=payload, headers=headers)
    assert response.status_code == 201
    assert response.json()["success"] is True
    assert response.json()["data"]["username"] == "post.user"
    user_id = response.json()["data"]["userId"]

    # 2. Get User via GET
    response = await async_client.get(f"/api/v1/users/{user_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["data"]["email"] == "post@avanthi.edu"

    # 3. Update User via PATCH
    update_payload = {
        "username": "updated.post.user"
    }
    response = await async_client.patch(f"/api/v1/users/{user_id}", json=update_payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["data"]["username"] == "updated.post.user"

    # 4. Search Users GET
    response = await async_client.get("/api/v1/users/search?query=updated", headers=headers)
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1

    # 5. Bulk Status Update PATCH
    status_payload = {
        "userIds": [user_id],
        "status": "SUSPENDED",
        "reason": "Security hold"
    }
    response = await async_client.patch("/api/v1/users/bulk-status", json=status_payload, headers=headers)
    assert response.status_code == 200
    assert user_id in response.json()["data"]["success"]

    # 6. Profile Me GET
    # Actually, setup_test_system created admin_user without Profile. Let's create profile for him manually so /profile/me works.
    admin_profile = Profile(
        profileId="PRF_000001",
        userId=admin_user.id,
        firstName="Admin",
        lastName="User"
    )
    await admin_profile.insert()
    admin_user.profile_id = admin_profile.id
    await admin_user.save()

    response = await async_client.get("/api/v1/profile/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["data"]["firstName"] == "Admin"

    # 7. Profile Me PATCH
    profile_payload = {
        "preferredName": "Main Admin",
        "bio": "System supervisor"
    }
    response = await async_client.patch("/api/v1/profile/me", json=profile_payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["data"]["preferredName"] == "Main Admin"

    # 8. Profile Avatar POST
    # Upload simulated file contents
    avatar_file = ("avatar.png", io.BytesIO(b"dummy image data"), "image/png")
    files = {"file": avatar_file}
    # Note: we need to manually pass headers without Content-Type as httpx sets boundary for multipart
    multipart_headers = {"Authorization": f"Bearer {token}", "x-tenant-slug": org.slug}
    response = await async_client.post("/api/v1/profile/avatar", files=files, headers=multipart_headers)
    assert response.status_code == 200
    assert "url" in response.json()["data"]

    # 9. Delete User via DELETE
    response = await async_client.delete(f"/api/v1/users/{user_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["success"] is True
