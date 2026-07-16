from typing import List, Optional
from datetime import datetime
from pymongo import IndexModel
from pydantic import Field, field_validator
from beanie import PydanticObjectId
import re

from app.models.base import BaseDocument
from app.models.org_engine.organization import validate_professional_id

class Module(BaseDocument):
    module_id: str = Field(..., alias="moduleId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    name: str = Field(..., min_length=2, max_length=50)
    slug: str = Field(..., min_length=2, max_length=30)
    version: str = Field(default="1.0.0")
    enabled: bool = Field(default=False)
    
    # Extended dependency/permissions plugin model settings
    dependencies: List[str] = Field(default_factory=list)
    required_permissions: List[str] = Field(default_factory=list, alias="requiredPermissions")
    required_modules: List[str] = Field(default_factory=list, alias="requiredModules")
    minimum_version: str = Field(default="1.0.0", alias="minimumVersion")

    @field_validator("module_id")
    @classmethod
    def validate_mod_id(cls, v: str) -> str:
        return validate_professional_id(v, "MOD")

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError("Module slug must contain only lowercase letters, numbers, and hyphens.")
        return v

    class Settings:
        name = "modules"
        indexes = [
            IndexModel("moduleId", unique=True),
            # organizationId + slug unique constraint
            IndexModel([("organizationId", 1), ("slug", 1)], unique=True),
            IndexModel("organizationId"),
        ]

from app.models.org_engine.config import FeatureFlag
