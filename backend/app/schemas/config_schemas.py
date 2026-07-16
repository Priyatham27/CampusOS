from pydantic import BaseModel, Field, ConfigDict, BeforeValidator
from datetime import datetime
from typing import Optional, List, Dict, Any
from typing_extensions import Annotated

from app.models.org_engine.config import (
    ConfigScope, ConfigEnvironment, ReleaseChannel
)

# Annotated validator to stringify MongoDB ObjectIDs before validation runs
PyObjectIdStr = Annotated[str, BeforeValidator(lambda v: str(v) if v is not None else None)]

schema_config = ConfigDict(
    populate_by_name=True,
    from_attributes=True,
    use_enum_values=True
)

# ==========================================
# CONFIGURATION SCHEMAS
# ==========================================

class ConfigurationCreateSchema(BaseModel):
    organizationId: Optional[str] = Field(default=None, alias="organizationId")
    module: Optional[str] = Field(default=None)
    userId: Optional[str] = Field(default=None, alias="userId")
    key: str = Field(..., min_length=2, max_length=100)
    value: Any = Field(...)
    type: str = Field(default="string")
    scope: ConfigScope = Field(default=ConfigScope.ORGANIZATION)
    encrypted: bool = Field(default=False)
    environment: ConfigEnvironment = Field(default=ConfigEnvironment.PRODUCTION)
    configVersion: str = Field(default="1.0.0", alias="configVersion")
    model_config = schema_config

class ConfigurationUpdateSchema(BaseModel):
    value: Any = Field(...)
    type: Optional[str] = None
    encrypted: Optional[bool] = None
    configVersion: Optional[str] = Field(None, alias="configVersion")
    model_config = schema_config

class ConfigurationResponseSchema(BaseModel):
    id: PyObjectIdStr = Field(..., alias="id")
    config_id: str = Field(..., alias="configId")
    organization_id: Optional[PyObjectIdStr] = Field(None, alias="organizationId")
    module: Optional[str] = None
    user_id: Optional[str] = Field(None, alias="userId")
    key: str
    value: Any
    type: str
    scope: ConfigScope
    encrypted: bool
    environment: ConfigEnvironment
    config_version: str = Field(..., validation_alias="config_version", serialization_alias="configVersion")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
    model_config = schema_config

# ==========================================
# FEATURE FLAG SCHEMAS
# ==========================================

class FeatureFlagCreateSchema(BaseModel):
    organizationId: Optional[str] = Field(default=None, alias="organizationId")
    key: str = Field(..., min_length=2, max_length=100)
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    category: str = Field(default="General")
    enabled: bool = Field(default=False)
    defaultValue: bool = Field(default=False, alias="defaultValue")
    environment: ConfigEnvironment = Field(default=ConfigEnvironment.PRODUCTION)
    rolloutPercentage: int = Field(default=100, ge=0, le=100, alias="rolloutPercentage")
    allowedRoles: List[str] = Field(default_factory=list, alias="allowedRoles")
    allowedUsers: List[str] = Field(default_factory=list, alias="allowedUsers")
    allowedDepartments: List[str] = Field(default_factory=list, alias="allowedDepartments")
    allowedPrograms: List[str] = Field(default_factory=list, alias="allowedPrograms")
    allowedSemesters: List[str] = Field(default_factory=list, alias="allowedSemesters")
    conditions: List[dict] = Field(default_factory=list)
    expiresAt: Optional[datetime] = Field(default=None, alias="expiresAt")
    metadata: dict = Field(default_factory=dict)
    model_config = schema_config

class FeatureFlagUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    category: Optional[str] = None
    enabled: Optional[bool] = None
    defaultValue: Optional[bool] = Field(None, alias="defaultValue")
    rolloutPercentage: Optional[int] = Field(None, ge=0, le=100, alias="rolloutPercentage")
    allowedRoles: Optional[List[str]] = Field(None, alias="allowedRoles")
    allowedUsers: Optional[List[str]] = Field(None, alias="allowedUsers")
    allowedDepartments: Optional[List[str]] = Field(None, alias="allowedDepartments")
    allowedPrograms: Optional[List[str]] = Field(None, alias="allowedPrograms")
    allowedSemesters: Optional[List[str]] = Field(None, alias="allowedSemesters")
    conditions: Optional[List[dict]] = None
    expiresAt: Optional[datetime] = Field(None, alias="expiresAt")
    metadata: Optional[dict] = None
    model_config = schema_config

class FeatureFlagResponseSchema(BaseModel):
    id: PyObjectIdStr = Field(..., alias="id")
    flag_id: str = Field(..., alias="flagId")
    organization_id: Optional[PyObjectIdStr] = Field(None, alias="organizationId")
    key: str
    name: str
    description: Optional[str] = None
    category: str
    enabled: bool
    default_value: bool = Field(..., alias="defaultValue")
    environment: ConfigEnvironment
    rollout_percentage: int = Field(..., alias="rolloutPercentage")
    allowed_roles: List[str] = Field(..., alias="allowedRoles")
    allowed_users: List[str] = Field(..., alias="allowedUsers")
    allowed_departments: List[str] = Field(..., alias="allowedDepartments")
    allowed_programs: List[str] = Field(..., alias="allowedPrograms")
    allowed_semesters: List[str] = Field(..., alias="allowedSemesters")
    conditions: List[dict]
    expires_at: Optional[datetime] = Field(None, alias="expiresAt")
    metadata: dict
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
    model_config = schema_config

class FeatureFlagEvaluationContext(BaseModel):
    userId: Optional[str] = Field(default=None, alias="userId")
    role: Optional[str] = Field(default=None)
    department: Optional[str] = Field(default=None)
    program: Optional[str] = Field(default=None)
    semester: Optional[str] = Field(default=None)
    environment: str = Field(default="PRODUCTION")
    model_config = schema_config
