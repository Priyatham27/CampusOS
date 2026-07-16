from typing import Optional, List
from beanie import PydanticObjectId
from app.models.identity.user import User
from app.models.org_engine.organization import Organization
from app.models.identity.rbac import UserRole, Role, RolePermission, Permission

class AuthenticationRepository:
    """
    Handles MongoDB database logic for the Authentication Engine.
    Resolves users, organizations, and RBAC roles/permissions boundaries.
    """
    async def find_user_by_email(self, email: str, org_id: PydanticObjectId, session=None) -> Optional[User]:
        return await User.find_one(
            User.email == email.lower(),
            User.organization_id == org_id,
            User.is_deleted == False,
            session=session
        )

    async def find_user_by_username(self, username: str, org_id: PydanticObjectId, session=None) -> Optional[User]:
        return await User.find_one(
            User.username == username.lower(),
            User.organization_id == org_id,
            User.is_deleted == False,
            session=session
        )

    async def find_org_by_id(self, org_id: PydanticObjectId, session=None) -> Optional[Organization]:
        return await Organization.find_one(
            Organization.id == org_id,
            Organization.is_deleted == False,
            session=session
        )

    async def find_org_by_slug(self, slug: str, session=None) -> Optional[Organization]:
        return await Organization.find_one(
            Organization.slug == slug.lower(),
            Organization.is_deleted == False,
            session=session
        )

    async def find_user_roles(self, user_id: PydanticObjectId, session=None) -> List[Role]:
        user_roles = await UserRole.find(UserRole.user_id == user_id, session=session).to_list()
        if not user_roles:
            return []
        role_ids = [ur.role_id for ur in user_roles]
        return await Role.find({"_id": {"$in": role_ids}, "isDeleted": False}, session=session).to_list()

    async def find_role_permissions(self, role_ids: List[PydanticObjectId], session=None) -> List[Permission]:
        if not role_ids:
            return []
        role_perms = await RolePermission.find({"roleId": {"$in": role_ids}}, session=session).to_list()
        if not role_perms:
            return []
        perm_ids = [rp.permission_id for rp in role_perms]
        return await Permission.find({"_id": {"$in": perm_ids}, "isDeleted": False}, session=session).to_list()
