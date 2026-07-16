import logging
from app.core.config import settings
from app.models.org_engine.organization import Organization
from app.models.identity.user import User, Profile
from app.models.identity.rbac import Role, Permission, UserRole, RolePermission
from app.services.capability import CapabilityService

logger = logging.getLogger("campusos.services.bootstrap")

class IdentityBootstrapService:
    """
    Validates and seeds the multi-tenant configuration and identity collections on startup.
    Ensures default permissions, roles, capabilities, and the super-admin user exist.
    """
    async def bootstrap(self) -> None:
        logger.info("Starting Identity Subsystem bootstrapping...")

        # 1. Ensure default organization (tenant) exists
        org = await Organization.find_one(Organization.slug == settings.DEFAULT_TENANT_SLUG)
        if not org:
            org = Organization(
                organizationId="ORG_000001",
                name="CampusOS Main Institution",
                shortName="CampusOS",
                slug=settings.DEFAULT_TENANT_SLUG,
                emailDomain="campusos.com",
                contactEmail="admin@campusos.com",
                status="ACTIVE"
            )
            await org.insert()
            logger.info(f"Default organization '{settings.DEFAULT_TENANT_SLUG}' created.")

        # 2. Verify and Seed Default Permissions
        default_perms = [
            ("PRM_000001", "core", "users", "read", "users:read"),
            ("PRM_000002", "core", "users", "manage", "users:manage"),
            ("PRM_000003", "core", "profiles", "read", "profile:read"),
            ("PRM_000004", "core", "profiles", "manage", "profile:manage"),
            ("PRM_000005", "core", "configs", "read", "configs:read"),
            ("PRM_000006", "core", "configs", "write", "configs:write"),
            ("PRM_000007", "core", "capabilities", "read", "capabilities:read"),
            ("PRM_000008", "core", "capabilities", "manage", "capabilities:manage"),
        ]
        
        db_perms = {}
        for p_id, mod, res, act, slug in default_perms:
            perm = await Permission.find_one(Permission.slug == slug)
            if not perm:
                perm = Permission(
                    permissionId=p_id,
                    module=mod,
                    resource=res,
                    action=act,
                    slug=slug
                )
                await perm.insert()
                logger.info(f"Permission '{slug}' bootstrapped.")
            db_perms[slug] = perm

        # 3. Verify and Seed Default Roles
        default_roles = [
            ("ROL_000001", "SuperAdmin", "super-admin", 1, True, ["users:read", "users:manage", "profile:read", "profile:manage", "configs:read", "configs:write", "capabilities:read", "capabilities:manage"]),
            ("ROL_000002", "Administrator", "admin", 2, False, ["users:read", "users:manage", "profile:read", "profile:manage", "configs:read", "configs:write"]),
            ("ROL_000003", "Student", "student", 10, False, ["profile:read", "profile:manage"]),
            ("ROL_000004", "Faculty", "faculty", 5, False, ["profile:read", "profile:manage"]),
        ]
        
        db_roles = {}
        for r_id, name, slug, priority, default_role, perm_slugs in default_roles:
            role = await Role.find_one(Role.slug == slug, Role.organization_id == org.id)
            if not role:
                role = Role(
                    roleId=r_id,
                    organizationId=org.id,
                    name=name,
                    slug=slug,
                    priority=priority,
                    default_role=default_role
                )
                await role.insert()
                logger.info(f"Role '{slug}' bootstrapped.")
            db_roles[slug] = role

            # Link Permissions to Role
            for p_slug in perm_slugs:
                if p_slug in db_perms:
                    rp_exists = await RolePermission.find_one(
                        RolePermission.role_id == role.id,
                        RolePermission.permission_id == db_perms[p_slug].id
                    )
                    if not rp_exists:
                        await RolePermission(
                            roleId=role.id,
                            permissionId=db_perms[p_slug].id
                        ).insert()

        # 4. Verify and Seed Default Admin User if no users exist
        user_count = await User.count()
        if user_count == 0:
            user = User(
                userId="USR_000001",
                organizationId=org.id,
                username="admin",
                email="admin@campusos.com",
                status="ACTIVE",
                emailVerified=True
            )
            await user.insert()

            # Assign SuperAdmin role mapping
            await UserRole(
                userId=user.id,
                roleId=db_roles["super-admin"].id
            ).insert()

            # Initialize base Profile
            profile = Profile(
                profileId="PRF_000001",
                userId=user.id,
                firstName="System",
                lastName="Administrator",
                timezone="UTC",
                language="en"
            )
            await profile.insert()

            user.profile_id = profile.id
            await user.save()

            # Create argon2 Credential
            from app.models.identity.credential import Credential, CredentialType
            from app.core.security import hash_password_argon2
            pw_hash = hash_password_argon2("AdminPassword123!")
            cred = Credential(
                credentialId="CRD_000001",
                userId=user.id,
                organizationId=org.id,
                type=CredentialType.PASSWORD,
                passwordHash=pw_hash,
                passwordHistory=[pw_hash],
                requiresPasswordChange=False
            )
            await cred.insert()
            logger.info("Default SuperAdmin user bootstrapped: admin / admin@campusos.com / AdminPassword123!")

        # 5. Seed default capabilities for the organization
        cap_svc = CapabilityService()
        await cap_svc.seed_default_capabilities(str(org.id))

        logger.info("Identity Subsystem bootstrapping completed successfully.")
