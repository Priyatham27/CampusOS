import secrets
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr

def generate_prefixed_id(prefix: str) -> str:
    """Generate professional prefixed unique identifiers (e.g. usr_3a1f9e2b)."""
    return f"{prefix}_{secrets.token_hex(6)}"

class TenantTheme(BaseModel):
    primary_color: str = "#4f46e5"
    secondary_color: str = "#0891b2"
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    custom_css: Optional[str] = None

class TenantConfig(BaseModel):
    theme: TenantTheme = Field(default_factory=TenantTheme)
    custom_domain: Optional[str] = None
    active_modules: List[str] = Field(default_factory=list) # List of active module slugs
    feature_flags: Dict[str, bool] = Field(default_factory=dict) # Module feature overrides

class Tenant(BaseModel):
    id: str = Field(default_factory=lambda: generate_prefixed_id("ten"), alias="_id")
    name: str
    slug: str
    config: TenantConfig = Field(default_factory=TenantConfig)
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "name": "State University",
                "slug": "state-univ",
                "config": {
                    "theme": {
                        "primary_color": "#1e3a8a",
                        "secondary_color": "#f59e0b"
                    },
                    "custom_domain": "portal.state.edu",
                    "active_modules": ["core"]
                },
                "is_active": True
            }
        }

class Role(BaseModel):
    id: str = Field(default_factory=lambda: generate_prefixed_id("rol"), alias="_id")
    name: str
    description: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)
    is_system: bool = False
    tenant_id: Optional[str] = None # None for global/system-wide roles, else scoped

    class Config:
        populate_by_name = True

class User(BaseModel):
    id: str = Field(default_factory=lambda: generate_prefixed_id("usr"), alias="_id")
    email: EmailStr
    hashed_password: str
    full_name: str
    tenant_id: str
    role_id: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

    class Config:
        populate_by_name = True

class AuditLog(BaseModel):
    id: str = Field(default_factory=lambda: generate_prefixed_id("aud"), alias="_id")
    tenant_id: str
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    action: str
    category: str = "activity" # activity, audit, error, security, api, performance
    details: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True

# Platform-wide System settings
class SystemSettingsBranding(BaseModel):
    platform_name: str = "CampusOS"
    logo_url: Optional[str] = None
    support_email: str = "support@campusos.com"

class SystemSettingsStorage(BaseModel):
    provider: str = "local" # local, cloudinary, s3
    upload_limit_mb: int = 10

class SystemSettingsEmail(BaseModel):
    smtp_host: str = "smtp.mailgun.org"
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    sender_name: str = "CampusOS Notifications"

class SystemSettingsSecurity(BaseModel):
    mfa_enabled: bool = False
    password_history_limit: int = 3
    cookie_secure: bool = False # False on dev, True in prod

class SystemSettings(BaseModel):
    id: str = Field(default="sys_settings", alias="_id")
    general: Dict[str, Any] = Field(default_factory=dict)
    branding: SystemSettingsBranding = Field(default_factory=SystemSettingsBranding)
    storage: SystemSettingsStorage = Field(default_factory=SystemSettingsStorage)
    email: SystemSettingsEmail = Field(default_factory=SystemSettingsEmail)
    security: SystemSettingsSecurity = Field(default_factory=SystemSettingsSecurity)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True

# Module Registry System
class ModuleDependency(BaseModel):
    module_slug: str
    min_version: str

class ModuleRegistry(BaseModel):
    id: str = Field(default_factory=lambda: generate_prefixed_id("mod"), alias="_id")
    name: str
    slug: str
    version: str
    status: str = "active" # active, disabled, deprecated
    dependencies: List[ModuleDependency] = Field(default_factory=list)
    permissions: List[Dict[str, str]] = Field(default_factory=list) # [{name, description}]
    routes: List[str] = Field(default_factory=list)
    navigation: Dict[str, Any] = Field(default_factory=dict)
    feature_flag: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
