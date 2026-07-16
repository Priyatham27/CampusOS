import logging
from typing import Optional, List, Dict, Any
from beanie import PydanticObjectId

from app.models.identity.rbac import Role, Permission, UserRole, RolePermission
from app.models.identity.policy import Policy
from app.repositories.authorization import AuthorizationRepository
from app.core.authorization_exceptions import (
    RoleNotFound,
    PermissionNotFound,
    ImmutableRole,
    AuthorizationDenied,
    InvalidPermission
)
from app.core.role_resolver import expand_roles
from app.core.policy_engine import match_wildcard

logger = logging.getLogger("campusos.service.authorization")

class AuthorizationService:
    def __init__(self):
        self.repo = AuthorizationRepository()

    # --- Role Management ---
    async def create_role(
        self,
        name: str,
        slug: str,
        organization_id: PydanticObjectId,
        priority: int = 10,
        description: Optional[str] = None,
        system_role: bool = False
    ) -> Role:
        existing = await self.repo.get_role_by_slug(organization_id, slug)
        if existing:
            raise InvalidPermission(f"Role with slug '{slug}' already exists in this organization.")

        role_count = await Role.find({}).count()
        role_id_str = f"ROL_{role_count + 1:06d}"

        role = Role(
            roleId=role_id_str,
            organizationId=organization_id,
            name=name,
            slug=slug,
            priority=priority,
            systemRole=system_role,
            description=description
        )
        return await self.repo.create_role(role)

    async def update_role(
        self,
        role_id: str,
        name: str,
        priority: int,
        description: Optional[str] = None,
        org_id: Optional[PydanticObjectId] = None
    ) -> Role:
        role = await self.repo.get_role_by_id(role_id)
        if not role:
            raise RoleNotFound("Role was not found.")

        # Tenancy boundary check
        if org_id and role.organization_id != org_id:
            raise AuthorizationDenied("Access denied to this role.")

        if role.system_role:
            raise ImmutableRole("System roles cannot be modified.")

        role.name = name
        role.priority = priority
        role.description = description
        return await self.repo.update_role(role)

    async def delete_role(self, role_id: str, org_id: Optional[PydanticObjectId] = None) -> None:
        role = await self.repo.get_role_by_id(role_id)
        if not role:
            raise RoleNotFound("Role was not found.")

        # Tenancy boundary check
        if org_id and role.organization_id != org_id:
            raise AuthorizationDenied("Access denied to this role.")

        if role.system_role:
            raise ImmutableRole("System roles cannot be deleted.")

        await self.repo.delete_role(role_id)

    async def assign_permission_to_role(
        self,
        role_id_str: str,
        permission_id_str: str,
        org_id: Optional[PydanticObjectId] = None,
        operator_roles: Optional[List[str]] = None
    ) -> None:
        operator_roles = operator_roles or []
        role = await self.repo.get_role_by_id(role_id_str)
        if not role:
            raise RoleNotFound("Role was not found.")

        # Tenancy boundary check
        if org_id and role.organization_id != org_id:
            raise AuthorizationDenied("Access denied to this role.")

        # Super admin restriction: Only super-admins can assign permissions to super-admin roles
        if role.slug in ("super-admin", "super_admin") and "super-admin" not in operator_roles and "super_admin" not in operator_roles:
            raise AuthorizationDenied("Only Super Admins can modify Super Admin role bindings.")

        perm = await self.repo.get_permission_by_id(permission_id_str)
        if not perm:
            raise PermissionNotFound("Permission was not found.")

        await self.repo.assign_permission_to_role(role.id, perm.id)

    async def remove_permission_from_role(
        self,
        role_id_str: str,
        permission_id_str: str,
        org_id: Optional[PydanticObjectId] = None,
        operator_roles: Optional[List[str]] = None
    ) -> None:
        operator_roles = operator_roles or []
        role = await self.repo.get_role_by_id(role_id_str)
        if not role:
            raise RoleNotFound("Role was not found.")

        # Tenancy boundary check
        if org_id and role.organization_id != org_id:
            raise AuthorizationDenied("Access denied to this role.")

        # Super admin restriction
        if role.slug in ("super-admin", "super_admin") and "super-admin" not in operator_roles and "super_admin" not in operator_roles:
            raise AuthorizationDenied("Only Super Admins can modify Super Admin role bindings.")

        perm = await self.repo.get_permission_by_id(permission_id_str)
        if not perm:
            raise PermissionNotFound("Permission was not found.")

        await self.repo.remove_permission_from_role(role.id, perm.id)

    # --- Permission Management ---
    async def create_permission(
        self,
        module: str,
        resource: str,
        action: str,
        slug: str,
        description: Optional[str] = None
    ) -> Permission:
        existing = await self.repo.get_permission_by_slug(slug)
        if existing:
            raise InvalidPermission(f"Permission with slug '{slug}' already exists.")

        count = await Permission.find({}).count()
        perm_id_str = f"PRM_{count + 1:06d}"

        perm = Permission(
            permissionId=perm_id_str,
            module=module,
            resource=resource,
            action=action,
            slug=slug,
            description=description
        )
        return await self.repo.create_permission(perm)

    async def update_permission(
        self,
        permission_id: str,
        description: Optional[str] = None
    ) -> Permission:
        perm = await self.repo.get_permission_by_id(permission_id)
        if not perm:
            raise PermissionNotFound("Permission was not found.")

        perm.description = description
        return await self.repo.update_permission(perm)

    async def delete_permission(self, permission_id: str) -> None:
        perm = await self.repo.get_permission_by_id(permission_id)
        if not perm:
            raise PermissionNotFound("Permission was not found.")

        # System permissions are protected
        if perm.slug.startswith("core:") or perm.slug.startswith("organization:"):
            raise ImmutableRole("System permissions cannot be deleted.")

        await self.repo.delete_permission(permission_id)

    # --- Policy Management ---
    async def create_policy(
        self,
        name: str,
        effect: str,
        subjects: List[str],
        actions: List[str],
        resources: List[str],
        organization_id: PydanticObjectId,
        priority: int = 10,
        description: Optional[str] = None,
        conditions: Optional[dict] = None
    ) -> Policy:
        count = await Policy.find({}).count()
        pol_id_str = f"POL_{count + 1:06d}"

        policy = Policy(
            policyId=pol_id_str,
            organizationId=organization_id,
            name=name,
            description=description,
            effect=effect,
            priority=priority,
            subjects=subjects,
            actions=actions,
            resources=resources,
            conditions=conditions
        )
        return await self.repo.create_policy(policy)

    # --- Effective Permission Resolving ---
    async def get_effective_permissions_for_user(
        self,
        user_id: PydanticObjectId,
        org_id: PydanticObjectId,
        active_roles: List[str],
        context_data: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Resolves the final list of allowed permission slugs for a user, combining
        RBAC role inheritance with explicit ALLOW/DENY policies.
        """
        context_data = context_data or {}
        user_id_str = str(user_id)

        # 1. Super Admin Override
        if "super-admin" in active_roles or "super_admin" in active_roles:
            all_perms = await Permission.find_all().to_list()
            return [p.slug for p in all_perms]

        # 2. Resolve inherited RBAC permissions
        expanded_roles = expand_roles(active_roles)
        role_objs = await Role.find({"organizationId": org_id, "slug": {"$in": expanded_roles}}).to_list()
        role_ids = [r.id for r in role_objs]

        base_permissions = []
        if role_ids:
            role_perms = await RolePermission.find({"roleId": {"$in": role_ids}}).to_list()
            perm_ids = [rp.permission_id for rp in role_perms]
            perms = await Permission.find({"_id": {"$in": perm_ids}}).to_list()
            base_permissions = [p.slug for p in perms]

        # 3. Apply policies
        from app.core.permission_evaluator import PermissionEvaluator
        evaluator = PermissionEvaluator()
        
        # We start with base permissions.
        # But policies can also explicitly grant (ALLOW) or revoke (DENY) permissions.
        # Let's get the list of all permissions in the system, and evaluate each one.
        all_perms = await Permission.find_all().to_list()
        effective = []
        
        from app.models.identity.user import User
        from app.models.org_engine.organization import Organization
        user = await User.find_one(User.id == user_id)
        org = await Organization.find_one(Organization.id == org_id)

        if not user or not org:
            return []

        for p in all_perms:
            try:
                allowed = await evaluator.evaluate(
                    user=user,
                    org=org,
                    active_roles=active_roles,
                    permission=p.slug,
                    resource="*",
                    context_data=context_data
                )
                if allowed:
                    effective.append(p.slug)
            except Exception:
                # DENY policy raised PolicyViolation exception, which means not allowed
                pass

        return effective
