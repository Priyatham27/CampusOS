from typing import List, Optional, Tuple, Dict, Any
from beanie import PydanticObjectId
from pymongo.client_session import ClientSession
from datetime import datetime

from app.models.identity.user import User

class UserRepository:
    """
    Repository for all operations on the User collection.
    Enforces soft-delete filters (isDeleted = False) and organization boundaries.
    """

    async def create(self, user: User, session: Optional[ClientSession] = None) -> User:
        """Insert a new User document."""
        return await user.insert(session=session)

    async def update(
        self,
        user: User,
        update_fields: dict,
        session: Optional[ClientSession] = None
    ) -> User:
        """Apply partial updates to a User document and sync internal fields."""
        # Clean update fields
        for key in ["_id", "id", "userId", "user_id", "organizationId", "organization_id", "created_at"]:
            update_fields.pop(key, None)

        db_update = {}
        for k, v in update_fields.items():
            prop = k
            if k == "profileId":
                prop = "profile_id"
            elif k == "accountType":
                prop = "account_type"
            elif k == "emailVerified":
                prop = "email_verified"
            elif k == "phoneVerified":
                prop = "phone_verified"
            elif k == "mfaEnabled":
                prop = "mfa_enabled"
            elif k == "lastLogin":
                prop = "last_login"
            elif k == "failedLoginAttempts":
                prop = "failed_login_attempts"
            elif k == "lockedUntil":
                prop = "locked_until"
            
            db_update[k] = v
            setattr(user, prop, v)

        if db_update:
            await User.find_one(User.id == user.id).update({"$set": db_update}, session=session)

        return user

    async def delete(self, user: User, reason: Optional[str] = None, session: Optional[ClientSession] = None) -> bool:
        """Logically soft-deletes a user."""
        await user.soft_delete(reason=reason, session=session)
        return True

    async def restore(self, user: User, reason: Optional[str] = None, session: Optional[ClientSession] = None) -> bool:
        """Restores a soft-deleted user."""
        await user.restore(reason=reason, session=session)
        return True

    async def find_by_id(
        self,
        user_id: str,
        org_id: Optional[PydanticObjectId] = None,
        session: Optional[ClientSession] = None
    ) -> Optional[User]:
        """Find an active user by their custom prefix user_id (e.g. USR_123456)."""
        query = [User.user_id == user_id, User.is_deleted == False]
        if org_id:
            query.append(User.organization_id == org_id)
        return await User.find_one(*query, session=session)

    async def find_by_beanie_id(
        self,
        id: PydanticObjectId,
        org_id: Optional[PydanticObjectId] = None,
        session: Optional[ClientSession] = None
    ) -> Optional[User]:
        """Find an active user by their MongoDB ObjectId."""
        query = [User.id == id, User.is_deleted == False]
        if org_id:
            query.append(User.organization_id == org_id)
        return await User.find_one(*query, session=session)

    async def find_by_username(
        self,
        username: str,
        org_id: PydanticObjectId,
        session: Optional[ClientSession] = None
    ) -> Optional[User]:
        """Find an active user by username within an organization (case-insensitive)."""
        return await User.find_one(
            User.username == username.lower(),
            User.organization_id == org_id,
            User.is_deleted == False,
            session=session
        )

    async def find_by_email(
        self,
        email: str,
        org_id: Optional[PydanticObjectId] = None,
        session: Optional[ClientSession] = None
    ) -> Optional[User]:
        """Find an active user by email (case-insensitive, optionally scoped to org)."""
        query = [User.email == email.lower(), User.is_deleted == False]
        if org_id:
            query.append(User.organization_id == org_id)
        return await User.find_one(*query, session=session)

    async def list(
        self,
        org_id: PydanticObjectId,
        skip: int = 0,
        limit: int = 10,
        sort_by: str = "createdAt",
        sort_order: str = "asc",
        filters: Optional[dict] = None,
        session: Optional[ClientSession] = None
    ) -> List[User]:
        """List active users matching standard pagination, sorting, and filter properties."""
        sort_map = {
            "createdAt": "created_at",
            "updatedAt": "updated_at",
            "username": "username",
            "email": "email",
            "userId": "user_id"
        }
        sort_field = sort_map.get(sort_by, "created_at")
        direction = -1 if sort_order.lower() == "desc" else 1

        query_expr = [User.organization_id == org_id, User.is_deleted == False]
        if filters:
            if "status" in filters and filters["status"]:
                query_expr.append(User.status == filters["status"])
            if "accountType" in filters and filters["accountType"]:
                query_expr.append(User.account_type == filters["accountType"])
            if "userIds" in filters and filters["userIds"]:
                query_expr.append({"_id": {"$in": [PydanticObjectId(uid) for uid in filters["userIds"]]}})

        cursor = User.find(*query_expr, session=session).sort([(sort_field, direction)]).skip(skip).limit(limit)
        return await cursor.to_list()

    async def count(
        self,
        org_id: PydanticObjectId,
        filters: Optional[dict] = None,
        session: Optional[ClientSession] = None
    ) -> int:
        """Count active users matching standard filter properties."""
        query_expr = [User.organization_id == org_id, User.is_deleted == False]
        if filters:
            if "status" in filters and filters["status"]:
                query_expr.append(User.status == filters["status"])
            if "accountType" in filters and filters["accountType"]:
                query_expr.append(User.account_type == filters["accountType"])
            if "userIds" in filters and filters["userIds"]:
                query_expr.append({"_id": {"$in": [PydanticObjectId(uid) for uid in filters["userIds"]]}})

        return await User.find(*query_expr, session=session).count()
