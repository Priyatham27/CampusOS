from pydantic import BaseModel, Field, ConfigDict, BeforeValidator
from datetime import datetime
from typing import Optional, Dict, Any
from typing_extensions import Annotated
from apps.api.app.models.identity.credential import CredentialType

PyObjectIdStr = Annotated[str, BeforeValidator(lambda v: str(v) if v is not None else None)]

schema_config = ConfigDict(
    populate_by_name=True,
    from_attributes=True,
    use_enum_values=True
)

class CredentialCreateSchema(BaseModel):
    user_id: str = Field(..., alias="userId")
    password: str = Field(...)
    type: CredentialType = Field(default=CredentialType.PASSWORD)
    model_config = schema_config

class PasswordChangeSchema(BaseModel):
    user_id: str = Field(..., alias="userId")
    current_password: str = Field(..., alias="currentPassword")
    new_password: str = Field(..., alias="newPassword")
    model_config = schema_config

class PasswordResetSchema(BaseModel):
    user_id: str = Field(..., alias="userId")
    token: str = Field(...)
    new_password: str = Field(..., alias="newPassword")
    model_config = schema_config

class ForcePasswordResetSchema(BaseModel):
    user_id: str = Field(..., alias="userId")
    new_password: str = Field(..., alias="newPassword")
    model_config = schema_config

class CredentialResponseSchema(BaseModel):
    id: PyObjectIdStr = Field(..., alias="id")
    credential_id: str = Field(..., alias="credentialId")
    user_id: PyObjectIdStr = Field(..., alias="userId")
    organization_id: PyObjectIdStr = Field(..., alias="organizationId")
    type: CredentialType
    password_changed_at: Optional[datetime] = Field(None, alias="passwordChangedAt")
    failed_login_attempts: int = Field(..., alias="failedLoginAttempts")
    locked_until: Optional[datetime] = Field(None, alias="lockedUntil")
    is_locked: bool = Field(..., alias="isLocked")
    requires_password_change: bool = Field(..., alias="requiresPasswordChange")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
    model_config = schema_config

class CredentialPatchSchema(BaseModel):
    is_locked: Optional[bool] = Field(None, alias="isLocked")
    requires_password_change: Optional[bool] = Field(None, alias="requiresPasswordChange")
    failed_login_attempts: Optional[int] = Field(None, alias="failedLoginAttempts")
    model_config = schema_config
