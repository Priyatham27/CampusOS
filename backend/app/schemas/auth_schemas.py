from pydantic import BaseModel, Field, EmailStr, ConfigDict, BeforeValidator
from typing import Optional, Dict, Any
from datetime import datetime
from typing_extensions import Annotated

PyObjectIdStr = Annotated[str, BeforeValidator(lambda v: str(v) if v is not None else None)]

schema_config = ConfigDict(
    populate_by_name=True,
    from_attributes=True,
    use_enum_values=True
)

class AuthUserResponse(BaseModel):
    id: PyObjectIdStr = Field(..., alias="id")
    user_id: str = Field(..., alias="userId")
    organization_id: PyObjectIdStr = Field(..., alias="organizationId")
    username: str
    email: EmailStr
    status: str
    account_type: str = Field(..., alias="accountType")
    email_verified: bool = Field(..., alias="emailVerified")
    mfa_enabled: bool = Field(..., alias="mfaEnabled")
    last_login: Optional[datetime] = Field(None, alias="lastLogin")
    created_at: Optional[datetime] = Field(None, alias="createdAt")
    model_config = schema_config

class AuthLoginRequest(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: str = Field(...)
    provider: str = Field(default="password")
    model_config = schema_config

class AuthRefreshRequest(BaseModel):
    refresh_token: str = Field(..., alias="refreshToken")
    model_config = schema_config

class AuthVerifyEmailRequest(BaseModel):
    user_id: str = Field(..., alias="userId")
    token: str = Field(...)
    model_config = schema_config

class AuthResponseDataSchema(BaseModel):
    access_token: str = Field(..., alias="accessToken")
    refresh_token: str = Field(..., alias="refreshToken")
    expires_in: int = Field(..., alias="expiresIn")
    user: AuthUserResponse
    model_config = schema_config
