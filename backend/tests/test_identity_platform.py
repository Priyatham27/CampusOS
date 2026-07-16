import pytest
import io
from beanie import PydanticObjectId
from httpx import AsyncClient

from app.core.config import settings
from app.models.org_engine.organization import Organization
from app.models.identity.user import User, Profile, UserStatus
from app.models.identity.rbac import Role, Permission, UserRole, RolePermission
from app.services.identity_cache import IdentityCacheService
from app.services.identity_bootstrap import IdentityBootstrapService
from app.services.identity_health import IdentityHealthService
from app.services.authentication import AuthenticationService

pytestmark = pytest.mark.asyncio

async def setup_bootstrap_test_environment() -> tuple[Organization, User, str, dict]:
    """Helper to bootstrap default system data and return (org, admin_user, token, headers)."""
    boot = IdentityBootstrapService()
    await boot.bootstrap()

    org = await Organization.find_one(Organization.slug == settings.DEFAULT_TENANT_SLUG)
    user = await User.find_one(User.email == "admin@campusos.com")

    # Generate token by logging in
    as_svc = AuthenticationService()
    payload = {
        "email": "admin@campusos.com",
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
    return org, user, token, headers

async def test_identity_bootstrap_logic():
    org, user, token, headers = await setup_bootstrap_test_environment()

    assert org is not None
    assert user is not None
    assert user.username == "admin"
    assert user.status == UserStatus.ACTIVE

    # Verify roles are seeded
    super_admin_role = await Role.find_one(Role.slug == "super-admin", Role.organization_id == org.id)
    assert super_admin_role is not None
    assert super_admin_role.name == "SuperAdmin"

    # Verify permissions are seeded
    read_perm = await Permission.find_one(Permission.slug == "users:read")
    assert read_perm is not None

    # Verify role permissions linking
    link = await RolePermission.find_one(
        RolePermission.role_id == super_admin_role.id,
        RolePermission.permission_id == read_perm.id
    )
    assert link is not None

async def test_identity_cache_operations():
    org, user, token, headers = await setup_bootstrap_test_environment()

    cache_svc = IdentityCacheService()
    org_id_str = str(org.id)
    user_id_str = str(user.id)

    # 1. Verify get on empty cache returns None
    cached = await cache_svc.get_cached_identity(org_id_str, user_id_str)
    assert cached is None

    # 2. Set cache
    test_payload = {
        "roles": ["super-admin"],
        "permissions": ["users:read", "users:manage"],
        "capabilities": ["platform", "organization"]
    }
    await cache_svc.set_cached_identity(org_id_str, user_id_str, test_payload, ttl_seconds=10)

    # 3. Verify cache hit
    cached = await cache_svc.get_cached_identity(org_id_str, user_id_str)
    assert cached is not None
    assert cached["roles"] == ["super-admin"]
    assert cached["permissions"] == ["users:read", "users:manage"]
    assert cached["capabilities"] == ["platform", "organization"]

    # 4. Invalidate cache
    await cache_svc.invalidate_cached_identity(org_id_str, user_id_str)
    cached = await cache_svc.get_cached_identity(org_id_str, user_id_str)
    assert cached is None

async def test_identity_health_service():
    org, user, token, headers = await setup_bootstrap_test_environment()

    health_svc = IdentityHealthService()
    report = await health_svc.get_health_status()

    assert report["status"] in ("healthy", "degraded")
    assert "mongodb" in report["components"]
    assert "cache" in report["components"]
    assert "session_store" in report["components"]
    assert "authorization" in report["components"]
    assert "runtime_configuration" in report["components"]

async def test_identity_api_endpoints(async_client):
    org, user, token, headers = await setup_bootstrap_test_environment()

    # Call health check endpoint
    response = await async_client.get("/api/v1/identity/health", headers=headers)
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "mongodb" in response.json()["data"]["components"]

    # Call profile me GET to verify context resolution and RequestContext / Logging middlewares
    response = await async_client.get("/api/v1/profile/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"]["firstName"] == "System"
