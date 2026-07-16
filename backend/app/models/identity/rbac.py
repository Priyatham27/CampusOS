from typing import Optional, List
from datetime import datetime
from pymongo import IndexModel
from pydantic import Field, field_validator
from beanie import PydanticObjectId
import re

from app.models.base import BaseDocument
from app.models.org_engine.organization import validate_professional_id

SLUG_REGEX = re.compile(r"^[a-z0-9\-_]+$")
PERMISSION_SLUG_REGEX = re.compile(r"^[a-z0-9\-_\*\.]+(?::|\.)[a-z0-9\-_\*\.]+(?::|\.)?[a-z0-9\-_\*\.]*$")

class Permission(BaseDocument):
    permission_id: str = Field(..., alias="permissionId")
    module: str = Field(..., min_length=2, max_length=50)       # e.g., "core", "events"
    resource: str = Field(..., min_length=2, max_length=50)     # e.g., "users", "certificates"
    action: str = Field(..., min_length=2, max_length=20)       # e.g., "read", "manage"
    slug: str = Field(..., min_length=3, max_length=100)        # e.g., "users:read"
    description: Optional[str] = Field(default=None, max_length=250)

    @field_validator("permission_id")
    @classmethod
    def validate_prm_id(cls, v: str) -> str:
        return validate_professional_id(v, "PRM")

    @field_validator("slug")
    @classmethod
    def validate_perm_slug(cls, v: str) -> str:
        if not PERMISSION_SLUG_REGEX.match(v) and v != "*":
            raise ValueError("Permission slug must follow action format (e.g. 'users:read' or '*').")
        return v.lower()

    class Settings:
        name = "permissions"
        indexes = [
            IndexModel("permissionId", unique=True),
            IndexModel("slug", unique=True),
            IndexModel("module"),
        ]

class Role(BaseDocument):
    role_id: str = Field(..., alias="roleId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    name: str = Field(..., min_length=2, max_length=50)
    slug: str = Field(..., min_length=2, max_length=50)
    priority: int = Field(default=10, ge=0, le=100)             # 0 is highest authority
    system_role: bool = Field(default=False, alias="systemRole")
    default_role: bool = Field(default=False, alias="defaultRole")
    description: Optional[str] = Field(default=None, max_length=250)

    @field_validator("role_id")
    @classmethod
    def validate_role_id(cls, v: str) -> str:
        return validate_professional_id(v, "ROL")

    @field_validator("slug")
    @classmethod
    def validate_role_slug(cls, v: str) -> str:
        if not SLUG_REGEX.match(v):
            raise ValueError("Role slug must contain only lowercase letters, numbers, hyphens, and underscores.")
        return v.lower()

    class Settings:
        name = "roles"
        indexes = [
            IndexModel("roleId", unique=True),
            IndexModel([("organizationId", 1), ("slug", 1)], unique=True),
            IndexModel("organizationId"),
            IndexModel("slug"),
        ]

class UserRole(BaseDocument):
    user_id: PydanticObjectId = Field(..., alias="userId")
    role_id: PydanticObjectId = Field(..., alias="roleId")
    assigned_by: Optional[str] = Field(default=None, alias="assignedBy") # USR_ID of supervisor
    assigned_at: datetime = Field(default_factory=datetime.utcnow, alias="assignedAt")

    class Settings:
        name = "user_roles"
        indexes = [
            IndexModel([("userId", 1), ("roleId", 1)], unique=True),
            IndexModel("userId"),
            IndexModel("roleId"),
        ]

class RolePermission(BaseDocument):
    role_id: PydanticObjectId = Field(..., alias="roleId")
    permission_id: PydanticObjectId = Field(..., alias="permissionId")

    class Settings:
        name = "role_permissions"
        indexes = [
            IndexModel([("roleId", 1), ("permissionId", 1)], unique=True),
            IndexModel("roleId"),
            IndexModel("permissionId"),
        ]
