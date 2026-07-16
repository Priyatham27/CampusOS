import pytest
import jwt
import hashlib
from datetime import datetime, timedelta
from beanie import PydanticObjectId
from httpx import AsyncClient

from app.core.config import settings
from app.core.ua_parser import parse_user_agent
from app.models.org_engine.organization import Organization
from app.models.identity.user import User, UserStatus
from app.models.identity.session import Session, Device, RefreshToken
from app.models.identity.rbac import UserRole, Role, RolePermission, Permission
from app.services.session import SessionService
from app.repositories.session import SessionRepository, DeviceRepository
from app.core.session_exceptions import (
    SessionNotFound,
    SessionExpired,
    RefreshTokenInvalid,
    RefreshTokenExpired
)

pytestmark = pytest.mark.asyncio

@pytest.fixture
def session_service():
    return SessionService()

@pytest.fixture
def session_repo():
    return SessionRepository()

@pytest.fixture
def device_repo():
    return DeviceRepository()

async def setup_test_context() -> tuple[Organization, User]:
    # Reset DB collections
    await Organization.find_all().delete()
    await User.find_all().delete()
    await Session.find_all().delete()
    await Device.find_all().delete()
    await RefreshToken.find_all().delete()
    await UserRole.find_all().delete()
    await Role.find_all().delete()
    await Permission.find_all().delete()

    org = Organization(
        organizationId="ORG_888888",
        name="Vignan University",
        shortName="Vignan",
        slug="vignan-uni",
        emailDomain="vignan.edu",
        contactEmail="admin@vignan.edu"
    )
    await org.insert()

    user = User(
        userId="USR_888888",
        organizationId=org.id,
        username="srinivas.k",
        email="srinivas@vignan.edu",
        status=UserStatus.ACTIVE,
        emailVerified=True
    )
    await user.insert()

    return org, user

async def test_ua_parsing_variants():
    # Test Desktop Windows Chrome
    chrome_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    browser, os, platform = parse_user_agent(chrome_ua)
    assert browser == "Chrome"
    assert os == "Windows"
    assert platform == "Desktop"

    # Test iPhone Mobile Safari
    safari_ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    browser, os, platform = parse_user_agent(safari_ua)
    assert browser == "Safari"
    assert os == "iOS"
    assert platform == "Mobile"

async def test_session_creation_rules(session_service, session_repo, device_repo):
    org, user = await setup_test_context()
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    ip = "192.168.10.15"

    session, access_token, refresh_token = await session_service.create_session(
        user_id=user.id,
        org_id=org.id,
        ip=ip,
        ua_string=ua
    )

    assert session.session_id.startswith("SES_")
    assert session.user_id == user.id
    assert session.ip_address == ip
    assert session.browser == "Chrome"

    # Verify device registered automatically
    device = await device_repo.find_device(session.device_id)
    assert device is not None
    assert device.device_name == "Chrome on Windows"
    assert device.platform == "Desktop"
    assert device.user_id == user.id

async def test_concurrent_session_limits(session_service):
    org, user = await setup_test_context()
    ua = "Mozilla/5.0"
    
    # Generate 6 sessions (default limit is 5)
    sessions = []
    for i in range(6):
        session, _, _ = await session_service.create_session(user.id, org.id, f"192.168.1.{i}", ua)
        sessions.append(session)

    # Oldest session should be revoked automatically (meaning 5 active remain)
    active_count = await Session.find(Session.user_id == user.id).count()
    assert active_count == 5

    # Check that the first session we created is gone (revoked)
    first_gone = await Session.find_one(Session.session_id == sessions[0].session_id)
    assert first_gone is None

async def test_refresh_token_rotation_and_replay_detection(session_service):
    org, user = await setup_test_context()
    ua = "Mozilla/5.0"
    
    session, access_token, refresh_token = await session_service.create_session(user.id, org.id, "127.0.0.1", ua)

    # First rotation (Valid)
    new_access, new_refresh = await session_service.refresh_session(refresh_token, "127.0.0.1", ua)
    assert new_access is not None
    assert new_refresh != refresh_token

    # Verify old token marked revoked in DB
    hashed_old = hashlib.sha256(refresh_token.encode()).hexdigest()
    old_rtk = await RefreshToken.find_one(RefreshToken.token_hash == hashed_old)
    assert old_rtk.revoked is True

    # Replay attack: attempt to reuse the first refresh token
    with pytest.raises(RefreshTokenInvalid):
        await session_service.refresh_session(refresh_token, "127.0.0.1", ua)

    # Invalidation verification: Replay attack should revoke all active sessions for this user!
    active_count = await Session.find(Session.user_id == user.id).count()
    assert active_count == 0

async def test_idle_and_absolute_timeouts(session_service, session_repo):
    org, user = await setup_test_context()
    ua = "Mozilla/5.0"
    
    session, _, _ = await session_service.create_session(user.id, org.id, "127.0.0.1", ua)

    # Test Absolute Timeout
    session.expires_at = datetime.utcnow() - timedelta(seconds=1)
    await session.save()
    session_repo.cache.delete_session(session.session_id)

    with pytest.raises(SessionExpired):
        await session_service.validate_session_activity(session.session_id)

    # Verify session deleted
    assert await Session.find_one(Session.session_id == session.session_id) is None

    # Recreate for Idle Timeout testing
    session2, _, _ = await session_service.create_session(user.id, org.id, "127.0.0.1", ua)
    session2.last_activity = datetime.utcnow() - timedelta(minutes=45) # default is 30 mins
    await session2.save()
    session_repo.cache.delete_session(session2.session_id)

    with pytest.raises(SessionExpired):
        await session_service.validate_session_activity(session2.session_id)

    assert await Session.find_one(Session.session_id == session2.session_id) is None

async def test_api_session_routes(async_client, session_service):
    org, user = await setup_test_context()
    ua = "Mozilla/5.0"
    
    # 1. Create Session via endpoint
    payload = {"userId": str(user.id), "organizationId": str(org.id)}
    res = await async_client.post("/api/v1/sessions/create", json=payload, headers={"User-Agent": ua, "x-tenant-slug": org.slug})
    assert res.status_code == 201
    data = res.json()["data"]
    access_token = data["accessToken"]
    refresh_token = data["refreshToken"]

    headers = {"Authorization": f"Bearer {access_token}", "x-tenant-slug": org.slug}

    # 2. Get Me session endpoint
    me_res = await async_client.get("/api/v1/sessions/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["data"]["isCurrent"] is True

    # 3. List active sessions endpoint
    list_res = await async_client.get("/api/v1/sessions", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]) == 1

    # 4. List devices endpoint
    devices_res = await async_client.get("/api/v1/sessions/devices", headers=headers)
    assert devices_res.status_code == 200
    assert len(devices_res.json()["data"]) == 1
    device_id = devices_res.json()["data"][0]["deviceId"]

    # 5. Trust device endpoint
    trust_payload = {"trusted": True}
    trust_res = await async_client.patch(
        f"/api/v1/sessions/devices/{device_id}/trust",
        json=trust_payload,
        headers=headers
    )
    assert trust_res.status_code == 200
    assert trust_res.json()["data"]["trusted"] is True

    # 6. Rotate refresh endpoint
    ref_payload = {"refreshToken": refresh_token}
    ref_res = await async_client.post("/api/v1/sessions/refresh", json=ref_payload, headers=headers)
    assert ref_res.status_code == 200
    new_access = ref_res.json()["data"]["accessToken"]

    # 7. Logout Endpoint
    headers_new = {"Authorization": f"Bearer {new_access}", "x-tenant-slug": org.slug}
    logout_res = await async_client.post("/api/v1/sessions/logout", headers=headers_new)
    assert logout_res.status_code == 200

    # Getting me should now fail with 401
    me_fail = await async_client.get("/api/v1/sessions/me", headers=headers_new)
    assert me_fail.status_code == 401
