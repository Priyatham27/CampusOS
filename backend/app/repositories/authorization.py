import logging
from typing import Optional, List, Dict, Any
from beanie import PydanticObjectId

from app.models.identity.rbac import Role, Permission, UserRole, RolePermission
from app.models.identity.policy import Policy
from app.services.cache_service import CacheService

logger = logging.getLogger("campusos.repository.authorization")

class AuthorizationRepository:
    def __init__(self):
        self.cache = CacheService()

    # --- Role Management ---
    async def create_role(self, role: Role) -> Role:
        await role.insert()
        return role

    async def get_role_by_id(self, role_id: str) -> Optional[Role]:
        return await Role.find_one(Role.role_id == role_id)

    async def get_role_by_slug(self, org_id: PydanticObjectId, slug: str) -> Optional[Role]:
        return await Role.find_one(Role.organization_id == org_id, Role.slug == slug)

    async def list_roles(self, org_id: PydanticObjectId) -> List[Role]:
        return await Role.find(Role.organization_id == org_id).to_list()

    async def update_role(self, role: Role) -> Role:
        await role.save()
        # Invalidate cache for users who might have this role
        await self.invalidate_role_cache_for_role(role.id)
        return role

    async def delete_role(self, role_id: str) -> None:
        role = await self.get_role_by_id(role_id)
        if role:
            # Delete assignments and the role itself
            await UserRole.find(UserRole.role_id == role.id).delete()
            await RolePermission.find(RolePermission.role_id == role.id).delete()
            await role.delete()
            await self.invalidate_role_cache_for_role(role.id)

    # --- Permission Management ---
    async def create_permission(self, permission: Permission) -> Permission:
        await permission.insert()
        return permission

    async def get_permission_by_id(self, permission_id: str) -> Optional[Permission]:
        return await Permission.find_one(Permission.permission_id == permission_id)

    async def get_permission_by_slug(self, slug: str) -> Optional[Permission]:
        return await Permission.find_one(Permission.slug == slug)

    async def list_permissions(self) -> List[Permission]:
        return await Permission.find_all().to_list()

    async def update_permission(self, permission: Permission) -> Permission:
        await permission.save()
        await self.invalidate_permission_cache_for_permission(permission.id)
        return permission

    async def delete_permission(self, permission_id: str) -> None:
        perm = await self.get_permission_by_id(permission_id)
        if perm:
            await RolePermission.find(RolePermission.permission_id == perm.id).delete()
            await perm.delete()
            await self.invalidate_permission_cache_for_permission(perm.id)

    # --- Role Permission Assignment ---
    async def assign_permission_to_role(self, role_id: PydanticObjectId, permission_id: PydanticObjectId) -> None:
        rp = RolePermission(role_id=role_id, permission_id=permission_id)
        # Avoid duplicate assignment
        existing = await RolePermission.find_one(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id
        )
        if not existing:
            await rp.insert()
            await self.invalidate_role_cache_for_role(role_id)

    async def remove_permission_from_role(self, role_id: PydanticObjectId, permission_id: PydanticObjectId) -> None:
        rp = await RolePermission.find_one(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id
        )
        if rp:
            await rp.delete()
            await self.invalidate_role_cache_for_role(role_id)

    async def list_role_permissions(self, role_id: PydanticObjectId) -> List[Permission]:
        role_perms = await RolePermission.find(RolePermission.role_id == role_id).to_list()
        perm_ids = [rp.permission_id for rp in role_perms]
        return await Permission.find({"_id": {"$in": perm_ids}}).to_list()

    # --- User Role Assignment ---
    async def assign_role_to_user(self, user_id: PydanticObjectId, role_id: PydanticObjectId, assigned_by: Optional[str] = None) -> None:
        ur = UserRole(user_id=user_id, role_id=role_id, assigned_by=assigned_by)
        existing = await UserRole.find_one(UserRole.user_id == user_id, UserRole.role_id == role_id)
        if not existing:
            await ur.insert()
            self.cache.delete_user_roles(str(user_id))
            self.cache.delete_user_permissions(str(user_id))

    async def remove_role_from_user(self, user_id: PydanticObjectId, role_id: PydanticObjectId) -> None:
        ur = await UserRole.find_one(UserRole.user_id == user_id, UserRole.role_id == role_id)
        if ur:
            await ur.delete()
            self.cache.delete_user_roles(str(user_id))
            self.cache.delete_user_permissions(str(user_id))

    async def list_user_roles(self, user_id: PydanticObjectId) -> List[Role]:
        cached = self.cache.get_user_roles(str(user_id))
        if cached is not None:
            # We cache role slugs. Retrieve Role documents from DB if needed, or cache slugs directly
            # For list_user_roles repository call, query DB to return Role documents
            pass
        user_roles = await UserRole.find(UserRole.user_id == user_id).to_list()
        role_ids = [ur.role_id for ur in user_roles]
        return await Role.find({"_id": {"$in": role_ids}}).to_list()

    async def list_user_role_slugs(self, user_id: PydanticObjectId) -> List[str]:
        cached = self.cache.get_user_roles(str(user_id))
        if cached is not None:
            return cached
        roles = await self.list_user_roles(user_id)
        slugs = [r.slug for r in roles]
        self.cache.set_user_roles(str(user_id), slugs)
        return slugs

    # --- Policy Management ---
    async def create_policy(self, policy: Policy) -> Policy:
        await policy.insert()
        self.cache.delete_org_policies(str(policy.organization_id))
        return policy

    async def get_policy_by_id(self, policy_id: str) -> Optional[Policy]:
        return await Policy.find_one(Policy.policy_id == policy_id)

    async def list_policies(self, org_id: PydanticObjectId) -> List[Policy]:
        return await Policy.find(Policy.organization_id == org_id).to_list()

    async def list_active_policies_for_org(self, org_id: PydanticObjectId) -> List[Policy]:
        cached = self.cache.get_org_policies(str(org_id))
        if cached is not None:
            return [Policy.model_validate(p) for p in cached]
        policies = await Policy.find(Policy.organization_id == org_id, Policy.is_active == True).to_list()
        self.cache.set_org_policies(str(org_id), [p.model_dump(by_alias=True) for p in policies])
        return policies

    async def update_policy(self, policy: Policy) -> Policy:
        await policy.save()
        self.cache.delete_org_policies(str(policy.organization_id))
        return policy

    async def delete_policy(self, policy_id: str) -> None:
        policy = await self.get_policy_by_id(policy_id)
        if policy:
            await policy.delete()
            self.cache.delete_org_policies(str(policy.organization_id))

    # --- Cache Invalidation Helpers ---
    async def invalidate_role_cache_for_role(self, role_id: PydanticObjectId) -> None:
        # Find all user roles linking to this role
        user_roles = await UserRole.find(UserRole.role_id == role_id).to_list()
        for ur in user_roles:
            self.cache.delete_user_roles(str(ur.user_id))
            self.cache.delete_user_permissions(str(ur.user_id))

    async def invalidate_permission_cache_for_permission(self, permission_id: PydanticObjectId) -> None:
        role_perms = await RolePermission.find(RolePermission.permission_id == permission_id).to_list()
        role_ids = [rp.role_id for rp in role_perms]
        user_roles = await UserRole.find({"roleId": {"$in": role_ids}}).to_list()
        for ur in user_roles:
            self.cache.delete_user_permissions(str(ur.user_id))
