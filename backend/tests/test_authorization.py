import pytest
import secrets
from datetime import datetime, timedelta, time, timezone
from beanie import PydanticObjectId
from httpx import AsyncClient

from app.core.config import settings
from app.core.role_resolver import expand_roles
from app.models.org_engine.organization import Organization
from app.models.identity.user import User, UserStatus
from app.models.identity.rbac import Role, Permission, UserRole, RolePermission
from app.models.identity.policy import Policy
from app.core.permission_evaluator import PermissionEvaluator
from app.core.decorators import require_permission
from app.core.authorization_exceptions import PolicyViolation, AuthorizationDenied
from app.services.authorization import AuthorizationService

pytestmark = pytest.mark.asyncio

@pytest.fixture
def auth_service():
    return AuthorizationService()

@pytest.fixture
def evaluator():
    return PermissionEvaluator()

async def setup_auth_test_context() -> tuple[Organization, User]:
    await Organization.find_all().delete()
    await User.find_all().delete()
    await Role.find_all().delete()
    await Permission.find_all().delete()
    await UserRole.find_all().delete()
    await RolePermission.find_all().delete()
    await Policy.find_all().delete()

    org = Organization(
        organizationId="ORG_999999",
        name="LPU University",
        shortName="LPU",
        slug="lpu-uni",
        emailDomain="lpu.in",
        contactEmail="admin@lpu.in"
    )
    await org.insert()

    user = User(
        userId="USR_999999",
        organizationId=org.id,
        username="john.doe",
        email="john@lpu.in",
        status=UserStatus.ACTIVE,
        emailVerified=True
    )
    await user.insert()

    return org, user

async def test_role_hierarchy_expansion():
    # Verify Super Admin inherits all
    sa_expanded = expand_roles(["super-admin"])
    assert "super-admin" in sa_expanded
    assert "org-admin" in sa_expanded
    assert "faculty" in sa_expanded
    assert "student" in sa_expanded
    assert "guest" in sa_expanded

    # Verify Faculty inherits coordinator, volunteer, student, guest
    fac_expanded = expand_roles(["faculty"])
    assert "faculty" in fac_expanded
    assert "student" in fac_expanded
    assert "guest" in fac_expanded
    assert "org-admin" not in fac_expanded

async def test_permission_evaluator_rbac_and_wildcards(evaluator):
    org, user = await setup_auth_test_context()

    # Create permissions
    p_create = Permission(permissionId="PRM_000001", module="events", resource="event", action="create", slug="events.create")
    await p_create.insert()
    p_publish = Permission(permissionId="PRM_000002", module="events", resource="event", action="publish", slug="events.publish")
    await p_publish.insert()

    # Create role
    role = Role(roleId="ROL_000001", organizationId=org.id, name="Coordinator", slug="event-coordinator")
    await role.insert()

    # Assign event-coordinator role to user
    ur = UserRole(userId=user.id, roleId=role.id)
    await ur.insert()

    # Default Deny
    allowed = await evaluator.evaluate(user, org, ["event-coordinator"], "events.create")
    assert allowed is False

    # Bind permission to role
    rp = RolePermission(roleId=role.id, permissionId=p_create.id)
    await rp.insert()

    # Now allowed
    allowed_new = await evaluator.evaluate(user, org, ["event-coordinator"], "events.create")
    assert allowed_new is True

    # Test wildcard support (e.g. events.*)
    p_wildcard = Permission(permissionId="PRM_000003", module="attendance", resource="any", action="any", slug="attendance.*")
    await p_wildcard.insert()
    await RolePermission(roleId=role.id, permissionId=p_wildcard.id).insert()

    assert await evaluator.evaluate(user, org, ["event-coordinator"], "attendance.scan") is True
    assert await evaluator.evaluate(user, org, ["event-coordinator"], "attendance.view") is True

async def test_policy_allow_deny_rules(evaluator):
    org, user = await setup_auth_test_context()

    # Base setup: Coordinator has events.create
    p_create = Permission(permissionId="PRM_000001", module="events", resource="event", action="create", slug="events.create")
    await p_create.insert()
    role = Role(roleId="ROL_000001", organizationId=org.id, name="Coordinator", slug="event-coordinator")
    await role.insert()
    await UserRole(userId=user.id, roleId=role.id).insert()
    await RolePermission(roleId=role.id, permissionId=p_create.id).insert()

    # 1. Base RBAC allows
    assert await evaluator.evaluate(user, org, ["event-coordinator"], "events.create") is True

    # 2. Add Deny Policy for Coordinator
    deny_pol = Policy(
        policyId="POL_000001",
        organizationId=org.id,
        name="Deny Coordinator Events",
        effect="DENY",
        priority=1, # higher priority (lower integer)
        subjects=["event-coordinator"],
        actions=["events.create"],
        resources=["*"]
    )
    await evaluator.repo.create_policy(deny_pol)

    # Deny Policy evaluation should raise PolicyViolation
    with pytest.raises(PolicyViolation):
        await evaluator.evaluate(user, org, ["event-coordinator"], "events.create")

async def test_time_and_department_conditions(evaluator):
    org, user = await setup_auth_test_context()

    # Allow policy under specific conditions
    cond_pol = Policy(
        policyId="POL_000002",
        organizationId=org.id,
        name="Working Hours Only",
        effect="ALLOW",
        priority=10,
        subjects=["student"],
        actions=["events.register"],
        resources=["*"],
        conditions={
            "time_range": {"start": "09:00", "end": "17:00"},
            "departments": ["CS", "IT"]
        }
    )
    await evaluator.repo.create_policy(cond_pol)

    # 1. Try out of time range (e.g. 20:00)
    allowed = await evaluator.evaluate(
        user=user,
        org=org,
        active_roles=["student"],
        permission="events.register",
        context_data={"time": "20:00", "department": "CS"}
    )
    assert allowed is False

    # 2. Try in working hours but wrong department
    allowed_wrong_dep = await evaluator.evaluate(
        user=user,
        org=org,
        active_roles=["student"],
        permission="events.register",
        context_data={"time": "14:00", "department": "Mechanical"}
    )
    assert allowed_wrong_dep is False

    # 3. Successful match
    allowed_success = await evaluator.evaluate(
        user=user,
        org=org,
        active_roles=["student"],
        permission="events.register",
        context_data={"time": "11:30", "department": "CS"}
    )
    assert allowed_success is True

async def test_authorization_api_endpoints(async_client):
    org, user = await setup_auth_test_context()

    # Create dummy session to resolve IdentityContext
    from app.models.identity.session import Session
    from datetime import datetime, timedelta
    session = Session(
        sessionId="SES_999999",
        userId=user.id,
        ipAddress="127.0.0.1",
        userAgent="Test UA",
        expiresAt=datetime.utcnow() + timedelta(days=1),
        lastActivity=datetime.utcnow()
    )
    await session.insert()

    # Issue access token
    import jwt
    iat = int(datetime.now(timezone.utc).timestamp())
    exp = iat + 3600
    jwt_payload = {
        "sub": str(user.id),
        "userId": str(user.id),
        "organizationId": str(org.id),
        "roles": ["super-admin"], # grant super admin to bypass route decorator checks
        "sessionId": "SES_999999",
        "type": "access",
        "iat": iat,
        "exp": exp,
        "iss": settings.APP_NAME,
        "aud": "campusos-api"
    }
    access_token = jwt.encode(jwt_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    headers = {"Authorization": f"Bearer {access_token}", "x-tenant-slug": org.slug}

    # 1. Create Role
    role_payload = {"name": "Librarian", "slug": "librarian", "priority": 15, "description": "Library admin"}
    res = await async_client.post("/api/v1/roles", json=role_payload, headers=headers)
    assert res.status_code == 201
    role_id = res.json()["data"]["roleId"]

    # 2. List Roles
    list_res = await async_client.get("/api/v1/roles", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]) > 0

    # 3. Create Permission
    perm_payload = {"module": "library", "resource": "book", "action": "issue", "slug": "library.book.issue", "description": "Issue books"}
    res_perm = await async_client.post("/api/v1/permissions", json=perm_payload, headers=headers)
    assert res_perm.status_code == 201
    perm_id = res_perm.json()["data"]["permissionId"]

    # 4. Bind Permission to Role
    bind_payload = {"permissionId": perm_id}
    bind_res = await async_client.post(f"/api/v1/roles/{role_id}/permissions", json=bind_payload, headers=headers)
    assert bind_res.status_code == 200

    # 5. Get Effective Permissions (permissions/me)
    me_res = await async_client.get("/api/v1/auth/permissions/me", headers=headers)
    assert me_res.status_code == 200

    # 6. Unbind Permission
    unbind_res = await async_client.delete(f"/api/v1/roles/{role_id}/permissions/{perm_id}", headers=headers)
    assert unbind_res.status_code == 200
