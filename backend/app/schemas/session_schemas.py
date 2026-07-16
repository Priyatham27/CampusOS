from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

schema_config = ConfigDict(
    populate_by_name=True,
    from_attributes=True,
    use_enum_values=True
)

class SessionCreateRequest(BaseModel):
    user_id: str = Field(..., alias="userId")
    organization_id: str = Field(..., alias="organizationId")
    model_config = schema_config

class SessionResponse(BaseModel):
    session_id: str = Field(..., alias="sessionId")
    ip_address: str = Field(..., alias="ipAddress")
    browser: Optional[str] = None
    platform: Optional[str] = None
    last_activity: datetime = Field(..., alias="lastActivity")
    expires_at: datetime = Field(..., alias="expiresAt")
    is_current: bool = Field(default=False, alias="isCurrent")
    model_config = schema_config

class DeviceResponse(BaseModel):
    device_id: str = Field(..., alias="deviceId")
    device_name: str = Field(..., alias="deviceName")
    browser: Optional[str] = None
    os: Optional[str] = None
    platform: Optional[str] = None
    trusted: bool
    last_login: datetime = Field(..., alias="lastLogin")
    model_config = schema_config

class DeviceTrustUpdate(BaseModel):
    trusted: bool
    model_config = schema_config
