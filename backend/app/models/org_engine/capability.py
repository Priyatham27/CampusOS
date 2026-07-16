from enum import Enum
from typing import List, Optional
from pymongo import IndexModel
from pydantic import Field, field_validator
from beanie import PydanticObjectId
import re

from app.models.base import BaseDocument
from app.models.org_engine.organization import validate_professional_id

class CapabilityCategory(str, Enum):
    Core = "Core"
    Academic = "Academic"
    Student = "Student"
    Faculty = "Faculty"
    Administration = "Administration"
    Events = "Events"
    Attendance = "Attendance"
    Certificates = "Certificates"
    Analytics = "Analytics"
    Communication = "Communication"
    Finance = "Finance"
    Hostel = "Hostel"
    Transport = "Transport"
    Library = "Library"
    Placement = "Placement"
    AI = "AI"
    Custom = "Custom"

class CapabilityStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    INSTALLED = "INSTALLED"
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"
    DEPRECATED = "DEPRECATED"
    COMING_SOON = "COMING_SOON"

class CapabilityVisibility(str, Enum):
    SYSTEM = "SYSTEM"
    ORGANIZATION = "ORGANIZATION"
    ADMIN = "ADMIN"
    PUBLIC = "PUBLIC"

class LicenseTier(str, Enum):
    FREE = "FREE"
    STARTER = "STARTER"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"

class Capability(BaseDocument):
    capability_id: str = Field(..., alias="capabilityId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    name: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., min_length=2, max_length=50)
    display_name: str = Field(..., alias="displayName", min_length=2, max_length=150)
    description: Optional[str] = Field(default=None, max_length=1000)
    category: CapabilityCategory = Field(default=CapabilityCategory.Custom)
    icon: Optional[str] = None
    capability_version: str = Field(default="1.0.0", alias="capabilityVersion")
    status: CapabilityStatus = Field(default=CapabilityStatus.AVAILABLE)
    visibility: CapabilityVisibility = Field(default=CapabilityVisibility.ORGANIZATION)
    dependencies: List[str] = Field(default_factory=list)
    required_capabilities: List[str] = Field(default_factory=list, alias="requiredCapabilities")
    default_enabled: bool = Field(default=False, alias="defaultEnabled")
    installed: bool = Field(default=False)
    enabled: bool = Field(default=False)
    license_required: bool = Field(default=False, alias="licenseRequired")
    license_tier: LicenseTier = Field(default=LicenseTier.FREE, alias="licenseTier")
    configuration: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)

    @field_validator("capability_id")
    @classmethod
    def validate_cap_id(cls, v: str) -> str:
        return validate_professional_id(v, "CAP")

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError("Capability slug must contain only lowercase letters, numbers, and hyphens.")
        return v

    class Settings:
        name = "capabilities"
        use_cache = False
        indexes = [
            IndexModel("capabilityId", unique=True),
            IndexModel([("organizationId", 1), ("slug", 1)], unique=True),
            IndexModel("organizationId"),
            IndexModel("category"),
            IndexModel("status"),
            IndexModel("enabled"),
        ]
