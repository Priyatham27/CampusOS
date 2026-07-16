from datetime import datetime
from typing import Optional, List, Dict, Any, Generic, TypeVar
from pydantic import BaseModel, EmailStr, Field

T = TypeVar("T")

# Standardized API Response Envelope
class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = ""
    data: Optional[T] = None
    meta: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)

# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# Permission Schemas
class PermissionResponse(BaseModel):
    name: str
    description: str
    module: str

    class Config:
        from_attributes = True

# Role Schemas
class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: List[str] = []

class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[List[str]] = None

class RoleResponse(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    description: Optional[str] = None
    permissions: List[str]
    is_system: bool
    tenant_id: Optional[str] = None

    class Config:
        from_attributes = True
        populate_by_name = True

# Tenant Config & Theme
class TenantThemeSchema(BaseModel):
    primary_color: str = "#4f46e5"
    secondary_color: str = "#0891b2"
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    custom_css: Optional[str] = None

class TenantConfigSchema(BaseModel):
    theme: TenantThemeSchema = Field(default_factory=TenantThemeSchema)
    custom_domain: Optional[str] = None
    active_modules: List[str] = []
    feature_flags: Dict[str, bool] = {}

# Tenant Schemas
class TenantCreate(BaseModel):
    name: str
    slug: str
    config: Optional[TenantConfigSchema] = None

class TenantUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[TenantConfigSchema] = None
    is_active: Optional[bool] = None

class TenantResponse(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    slug: str
    config: TenantConfigSchema
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True

# User Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    tenant_id: str
    role_id: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role_id: Optional[str] = None
    is_active: Optional[bool] = None

class UserResponse(BaseModel):
    id: str = Field(..., alias="_id")
    email: EmailStr
    full_name: str
    tenant_id: str
    role_id: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True
        populate_by_name = True

class UserWithDetails(UserResponse):
    tenant: Optional[TenantResponse] = None
    role: Optional[RoleResponse] = None

# Audit Log Schema
class AuditLogResponse(BaseModel):
    id: str = Field(..., alias="_id")
    tenant_id: str
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    action: str
    category: str
    details: Dict[str, Any]
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True

# System Settings Schemas
class SystemSettingsBrandingSchema(BaseModel):
    platform_name: str
    logo_url: Optional[str] = None
    support_email: EmailStr

class SystemSettingsStorageSchema(BaseModel):
    provider: str
    upload_limit_mb: int

class SystemSettingsEmailSchema(BaseModel):
    smtp_host: str
    smtp_port: int
    smtp_user: Optional[str] = None
    sender_name: str

class SystemSettingsSecuritySchema(BaseModel):
    mfa_enabled: bool
    password_history_limit: int
    cookie_secure: bool

class SystemSettingsResponse(BaseModel):
    id: str = Field(..., alias="_id")
    general: Dict[str, Any]
    branding: SystemSettingsBrandingSchema
    storage: SystemSettingsStorageSchema
    email: SystemSettingsEmailSchema
    security: SystemSettingsSecuritySchema
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True
