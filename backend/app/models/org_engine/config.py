from enum import Enum
from typing import List, Optional, Any
from datetime import datetime
from pymongo import IndexModel
from pydantic import Field, field_validator
from beanie import PydanticObjectId

from app.models.base import BaseDocument
from app.models.org_engine.organization import validate_professional_id

class ConfigScope(str, Enum):
    GLOBAL = "GLOBAL"
    SYSTEM = "SYSTEM"
    ORGANIZATION = "ORGANIZATION"
    MODULE = "MODULE"
    USER = "USER"

class ConfigEnvironment(str, Enum):
    LOCAL = "LOCAL"
    DEVELOPMENT = "DEVELOPMENT"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"

class ReleaseChannel(str, Enum):
    STABLE = "STABLE"
    BETA = "BETA"
    ALPHA = "ALPHA"
    EXPERIMENTAL = "EXPERIMENTAL"

class Configuration(BaseDocument):
    config_id: str = Field(..., alias="configId")
    organization_id: Optional[PydanticObjectId] = Field(default=None, alias="organizationId")
    module: Optional[str] = Field(default=None)
    user_id: Optional[str] = Field(default=None, alias="userId")
    key: str = Field(..., min_length=2, max_length=100)
    value: Any = Field(...)
    type: str = Field(...)  # e.g., "boolean", "integer", "float", "string", "json"
    scope: ConfigScope = Field(default=ConfigScope.ORGANIZATION)
    encrypted: bool = Field(default=False)
    environment: ConfigEnvironment = Field(default=ConfigEnvironment.PRODUCTION)
    config_version: str = Field(default="1.0.0", alias="configVersion")

    @field_validator("config_id")
    @classmethod
    def validate_cfg_id(cls, v: str) -> str:
        return validate_professional_id(v, "CFG")

    class Settings:
        name = "configurations"
        use_cache = False
        indexes = [
            IndexModel("configId", unique=True),
            IndexModel([("organizationId", 1), ("module", 1), ("userId", 1), ("key", 1), ("scope", 1), ("environment", 1)], unique=True),
            IndexModel("key"),
            IndexModel("scope"),
            IndexModel("environment"),
        ]

class FeatureFlag(BaseDocument):
    flag_id: str = Field(..., alias="flagId")
    organization_id: Optional[PydanticObjectId] = Field(default=None, alias="organizationId")
    key: str = Field(..., min_length=2, max_length=100)
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    category: str = Field(default="General")
    enabled: bool = Field(default=False)
    default_value: bool = Field(default=False, alias="defaultValue")
    environment: ConfigEnvironment = Field(default=ConfigEnvironment.PRODUCTION)
    rollout_percentage: int = Field(default=100, ge=0, le=100, alias="rolloutPercentage")
    allowed_roles: List[str] = Field(default_factory=list, alias="allowedRoles")
    allowed_users: List[str] = Field(default_factory=list, alias="allowedUsers")
    allowed_departments: List[str] = Field(default_factory=list, alias="allowedDepartments")
    allowed_programs: List[str] = Field(default_factory=list, alias="allowedPrograms")
    allowed_semesters: List[str] = Field(default_factory=list, alias="allowedSemesters")
    conditions: List[dict] = Field(default_factory=list)
    expires_at: Optional[datetime] = Field(default=None, alias="expiresAt")
    metadata: dict = Field(default_factory=dict)

    @field_validator("flag_id")
    @classmethod
    def validate_flg_id(cls, v: str) -> str:
        return validate_professional_id(v, "FLG")

    class Settings:
        name = "feature_flags"
        use_cache = False
        indexes = [
            IndexModel("flagId", unique=True),
            IndexModel([("organizationId", 1), ("key", 1), ("environment", 1)], unique=True),
            IndexModel("key"),
            IndexModel("environment"),
        ]
