from pydantic import BaseModel, Field, ConfigDict, BeforeValidator
from datetime import datetime
from typing import Optional, List, Dict, Any
from typing_extensions import Annotated

from apps.api.app.models.org_engine.capability import (
    CapabilityCategory, CapabilityStatus, CapabilityVisibility, LicenseTier
)

# Annotated validator to stringify MongoDB ObjectIDs before validation runs
PyObjectIdStr = Annotated[str, BeforeValidator(lambda v: str(v) if v is not None else None)]

schema_config = ConfigDict(
    populate_by_name=True,
    from_attributes=True,
    use_enum_values=True
)

class CapabilityCreateSchema(BaseModel):
    organizationId: str = Field(..., alias="organizationId")
    name: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., min_length=2, max_length=50)
    displayName: str = Field(..., alias="displayName", min_length=2, max_length=150)
    description: Optional[str] = Field(default=None, max_length=1000)
    category: CapabilityCategory = Field(default=CapabilityCategory.Custom)
    icon: Optional[str] = Field(default=None)
    version: str = Field(default="1.0.0")
    status: CapabilityStatus = Field(default=CapabilityStatus.AVAILABLE)
    visibility: CapabilityVisibility = Field(default=CapabilityVisibility.ORGANIZATION)
    dependencies: List[str] = Field(default_factory=list)
    requiredCapabilities: List[str] = Field(default_factory=list, alias="requiredCapabilities")
    defaultEnabled: bool = Field(default=False, alias="defaultEnabled")
    installed: bool = Field(default=False)
    enabled: bool = Field(default=False)
    licenseRequired: bool = Field(default=False, alias="licenseRequired")
    licenseTier: LicenseTier = Field(default=LicenseTier.FREE, alias="licenseTier")
    configuration: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    model_config = schema_config

class CapabilityUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    slug: Optional[str] = Field(None, min_length=2, max_length=50)
    displayName: Optional[str] = Field(None, alias="displayName", min_length=2, max_length=150)
    description: Optional[str] = Field(None, max_length=1000)
    category: Optional[CapabilityCategory] = None
    icon: Optional[str] = None
    version: Optional[str] = None
    status: Optional[CapabilityStatus] = None
    visibility: Optional[CapabilityVisibility] = None
    dependencies: Optional[List[str]] = None
    requiredCapabilities: Optional[List[str]] = Field(None, alias="requiredCapabilities")
    defaultEnabled: Optional[bool] = Field(None, alias="defaultEnabled")
    installed: Optional[bool] = None
    enabled: Optional[bool] = None
    licenseRequired: Optional[bool] = Field(None, alias="licenseRequired")
    licenseTier: Optional[LicenseTier] = Field(None, alias="licenseTier")
    configuration: Optional[dict] = None
    metadata: Optional[dict] = None
    model_config = schema_config

class CapabilityResponseSchema(BaseModel):
    id: PyObjectIdStr = Field(..., alias="id")
    capability_id: str = Field(..., alias="capabilityId")
    organization_id: PyObjectIdStr = Field(..., alias="organizationId")
    name: str
    slug: str
    display_name: str = Field(..., alias="displayName")
    description: Optional[str] = None
    category: CapabilityCategory
    icon: Optional[str] = None
    version: str = Field(..., validation_alias="capability_version", serialization_alias="version")
    status: CapabilityStatus
    visibility: CapabilityVisibility
    dependencies: List[str]
    required_capabilities: List[str] = Field(..., alias="requiredCapabilities")
    default_enabled: bool = Field(..., alias="defaultEnabled")
    installed: bool
    enabled: bool
    license_required: bool = Field(..., alias="licenseRequired")
    license_tier: LicenseTier = Field(..., alias="licenseTier")
    configuration: dict
    metadata: dict
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
    model_config = schema_config
