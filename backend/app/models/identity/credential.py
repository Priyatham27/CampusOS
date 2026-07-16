from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import Field, field_validator
from beanie import PydanticObjectId
from pymongo import IndexModel

from app.models.base import BaseDocument
from app.models.org_engine.organization import validate_professional_id

class CredentialType(str, Enum):
    PASSWORD = "password"
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    PASSKEY = "passkey"
    MAGIC_LINK = "magic_link"

class Credential(BaseDocument):
    credential_id: str = Field(..., alias="credentialId")
    user_id: PydanticObjectId = Field(..., alias="userId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    type: CredentialType = Field(default=CredentialType.PASSWORD)
    
    # Password fields
    password_hash: Optional[str] = Field(default=None, alias="passwordHash")
    password_history: List[str] = Field(default_factory=list, alias="passwordHistory")
    password_changed_at: Optional[datetime] = Field(default=None, alias="passwordChangedAt")
    
    # Account locking and failure tracking
    failed_login_attempts: int = Field(default=0, alias="failedLoginAttempts")
    locked_until: Optional[datetime] = Field(default=None, alias="lockedUntil")
    is_locked: bool = Field(default=False, alias="isLocked")
    
    # Flag to force reset password
    requires_password_change: bool = Field(default=False, alias="requiresPasswordChange")
    
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("credential_id")
    @classmethod
    def validate_crd_id(cls, v: str) -> str:
        return validate_professional_id(v, "CRD")

    class Settings:
        name = "credentials"
        indexes = [
            IndexModel("credentialId", unique=True),
            IndexModel([("userId", 1), ("type", 1)], unique=True),
            IndexModel("organizationId"),
            IndexModel("userId"),
        ]
