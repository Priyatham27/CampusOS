import pytest
import jwt
import hashlib
from datetime import datetime, timedelta
from beanie import PydanticObjectId
from httpx import AsyncClient

from apps.api.app.core.config import settings
from apps.api.app.models.org_engine.organization import Organization
from apps.api.app.models.identity.user import User, UserStatus
from apps.api.app.models.identity.credential import Credential, CredentialType
from apps.api.app.models.identity.security import SecurityEvent, SecurityEventType, EmailVerificationToken
from apps.api.app.models.identity.session import Session, RefreshToken
from apps.api.app.models.identity.rbac import UserRole, Role, RolePermission, Permission
from apps.api.app.services.authentication import AuthenticationService
from apps.api.app.services.credential import CredentialService
from apps.api.app.core.auth_exceptions import (
    AuthenticationFailed,
    AccountLocked,
    AccountDisabled,
    EmailNotVerified,
    InvalidToken
)

pytestmark = pytest.mark.asyncio

@pytest.fixture
def auth_service():
    return AuthenticationService()

@pytest.fixture
def credential_service():
    return CredentialService()

async def setup_test_org_user_rbac() -> tuple[Organization, User, Role, Permission]:
    # 1. Create Organization
    org = Organization(
        organizationId="ORG_999999",
        name="Avanthi Institute of Engineering",
        shortName="Avanthi",
        slug="avanthi-inst",
        emailDomain="avanthi.edu",
        contactEmail="admin@avanthi.edu"
    )
    await org.insert()

    # 2. Create User
    user = User(
        userId="USR_999999",
        organizationId=org.id,
        username="john.doe",
        email="john@avanthi.edu",
        status=UserStatus.ACTIVE,
        emailVerified=True
    )
    await user.insert()

    # 3. Create Role
    role = Role(
        roleId="ROL_999999",
        organizationId=org.id,
        name="Student",
        slug="student",
        priority=10,
        systemRole=True
    )
    await role.insert()

    # 4. Map User to Role
    ur = UserRole(userId=user.id, roleId=role.id)
    await ur.insert()

    # 5. Create Permission
    perm = Permission(
        permissionId="PRM_999999",
        module="core",
        resource="settings",
        action="read",
        slug="settings:read"
    )
    await perm.insert()

    # 6. Map Role to Permission
    rp = RolePermission(roleId=role.id, permissionId=perm.id)
    await rp.insert()

    return org, user, role, perm

async def test_successful_login_password_provider(auth_service, credential_service):
    org, user, role, perm = await setup_test_org_user_rbac()
    
    # Enable credential
    await credential_service.create_credential(
        user_id_str=str(user.id),
        password="SecurePassword123!"
    )

    # Perform login
    payload = {
        "email": "john@avanthi.edu",
        "password": "SecurePassword123!",
        "provider": "password"
    }
    
    res = await auth_service.login(
        org_id_str=str(org.id),
        payload=payload,
        user_agent="Mozilla/5.0 ...",
        ip_address="192.168.1.100"
    )

    assert "accessToken" in res
    assert "refreshToken" in res
    assert res["expiresIn"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert res["user"].email == "john@avanthi.edu"

    # Decode and verify Access Token payload claims
    decoded = jwt.decode(res["accessToken"], settings.SECRET_KEY, options={"verify_aud": False}, algorithms=[settings.ALGORITHM])
    assert decoded["sub"] == str(user.id)
    assert decoded["userId"] == str(user.id)
    assert decoded["organizationId"] == str(org.id)
    assert "student" in decoded["roles"]
    assert "settings:read" in decoded["permissions"]
    assert decoded["iss"] == settings.APP_NAME
    assert decoded["aud"] == "campusos-api"
    assert "sessionId" in decoded

    # Check session exists in DB
    session_db = await Session.find_one(Session.session_id == decoded["sessionId"])
    assert session_db is not None
    assert session_db.user_id == user.id
    assert session_db.ip_address == "192.168.1.100"

    # Check refresh token exists in DB
    hashed_rtk = hashlib.sha256(res["refreshToken"].encode("utf-8")).hexdigest()
    rtk_db = await RefreshToken.find_one(RefreshToken.token_hash == hashed_rtk)
    assert rtk_db is not None
    assert rtk_db.session_id == session_db.id

async def test_login_unverified_email_fails(auth_service, credential_service):
    org, user, role, perm = await setup_test_org_user_rbac()
    user.email_verified = False
    await user.save()

    # Create token for email verification
    evt = EmailVerificationToken(
        verificationTokenId="EVT_999999",
        userId=user.id,
        tokenHash=hashlib.sha256("token123".encode()).hexdigest(),
        expiresAt=datetime.utcnow() + timedelta(hours=1),
        verified=False
    )
    await evt.insert()

    # Make credential creation possible (temporarily setting emailVerified = True to bypass verification trigger block)
    user.email_verified = True
    await user.save()
    await credential_service.create_credential(user_id_str=str(user.id), password="SecurePassword123!")
    user.email_verified = False
    await user.save()

    payload = {
        "email": "john@avanthi.edu",
        "password": "SecurePassword123!",
        "provider": "password"
    }

    with pytest.raises(EmailNotVerified):
        await auth_service.login(org_id_str=str(org.id), payload=payload, user_agent="Mozilla/5.0")

async def test_login_disabled_account_fails(auth_service, credential_service):
    org, user, role, perm = await setup_test_org_user_rbac()
    user.status = UserStatus.SUSPENDED
    await user.save()

    payload = {
        "email": "john@avanthi.edu",
        "password": "SecurePassword123!",
        "provider": "password"
    }

    with pytest.raises(AccountDisabled):
        await auth_service.login(org_id_str=str(org.id), payload=payload, user_agent="Mozilla/5.0")

async def test_timing_safe_invalid_user_login(auth_service):
    org, user, role, perm = await setup_test_org_user_rbac()
    
    payload = {
        "email": "nonexistent@avanthi.edu",
        "password": "WrongPassword!",
        "provider": "password"
    }
    
    with pytest.raises(AuthenticationFailed):
        await auth_service.login(org_id_str=str(org.id), payload=payload, user_agent="Mozilla/5.0")

async def test_refresh_token_cycle(auth_service, credential_service):
    org, user, role, perm = await setup_test_org_user_rbac()
    await credential_service.create_credential(user_id_str=str(user.id), password="SecurePassword123!")

    # Login
    payload = {
        "email": "john@avanthi.edu",
        "password": "SecurePassword123!"
    }
    login_res = await auth_service.login(org_id_str=str(org.id), payload=payload, user_agent="Mozilla/5.0")
    
    # Refresh token
    refresh_res = await auth_service.refresh_access_token(login_res["refreshToken"])
    assert "accessToken" in refresh_res
    assert refresh_res["refreshToken"] == login_res["refreshToken"]

    # Invalidate token
    await auth_service.logout(
        session_id_str=jwt.decode(refresh_res["accessToken"], settings.SECRET_KEY, options={"verify_aud": False}, algorithms=[settings.ALGORITHM])["sessionId"]
    )

    # Refresh again should fail
    with pytest.raises(InvalidToken):
        await auth_service.refresh_access_token(login_res["refreshToken"])

async def test_api_endpoints_login_logout_refresh_me(async_client, credential_service):
    org, user, role, perm = await setup_test_org_user_rbac()
    await credential_service.create_credential(user_id_str=str(user.id), password="SecurePassword123!")

    # 1. Login Endpoint
    login_payload = {
        "email": "john@avanthi.edu",
        "password": "SecurePassword123!",
        "provider": "password"
    }
    headers = {"x-tenant-slug": org.slug}
    response = await async_client.post("/api/v1/auth/login", json=login_payload, headers=headers)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert "accessToken" in res_data["data"]
    assert "refreshToken" in res_data["data"]
    
    access_token = res_data["data"]["accessToken"]
    refresh_token = res_data["data"]["refreshToken"]

    # 2. Get Me Endpoint
    auth_headers = {"Authorization": f"Bearer {access_token}", "x-tenant-slug": org.slug}
    me_response = await async_client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_response.status_code == 200
    assert me_response.json()["data"]["email"] == "john@avanthi.edu"

    # 3. Refresh Endpoint
    refresh_payload = {"refreshToken": refresh_token}
    ref_response = await async_client.post("/api/v1/auth/refresh", json=refresh_payload, headers=headers)
    assert ref_response.status_code == 200
    assert "accessToken" in ref_response.json()["data"]

    # 4. Logout Endpoint
    logout_response = await async_client.post("/api/v1/auth/logout", headers=auth_headers)
    assert logout_response.status_code == 200
    assert logout_response.json()["success"] is True

    # Get Me should now fail
    me_fail = await async_client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_fail.status_code == 401
