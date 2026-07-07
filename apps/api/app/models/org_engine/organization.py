from enum import Enum
from typing import Optional, List
from datetime import datetime
from pymongo import IndexModel
from pydantic import Field, EmailStr, BaseModel, field_validator, ConfigDict
from pydantic.alias_generators import to_camel
from beanie import PydanticObjectId
import re

from apps.api.app.models.base import BaseDocument

class OrganizationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DEACTIVATED = "DEACTIVATED"

class SubscriptionPlan(str, Enum):
    FREE = "FREE"
    BASIC = "BASIC"
    PREMIUM = "PREMIUM"
    ENTERPRISE = "ENTERPRISE"

class SubscriptionStatus(str, Enum):
    TRIAL = "TRIAL"
    ACTIVE = "ACTIVE"
    PAST_DUE = "PAST_DUE"
    CANCELLED = "CANCELLED"

HEX_COLOR_REGEX = re.compile(r"^#(?:[0-9a-fA-F]{3}){1,2}$")
UPPER_PREFIX_ID_REGEX = re.compile(r"^[A-Z]{3,}_[0-9]{6,}$")

def validate_hex_color(value: str) -> str:
    if not HEX_COLOR_REGEX.match(value):
        raise ValueError(f"Invalid Hex Color pattern: {value}. Must be a valid hex color (e.g., #4F46E5)")
    return value

def validate_professional_id(value: str, prefix: str) -> str:
    if not UPPER_PREFIX_ID_REGEX.match(value) or not value.startswith(f"{prefix}_"):
        raise ValueError(f"Invalid ID format: '{value}'. Must be uppercase prefix '{prefix}_' followed by at least 6 digits (e.g. {prefix}_000001).")
    return value

class BaseNestedModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        use_enum_values=True,
    )

class SubscriptionInfo(BaseNestedModel):
    plan: SubscriptionPlan = Field(default=SubscriptionPlan.FREE)
    status: SubscriptionStatus = Field(default=SubscriptionStatus.TRIAL)
    trial_start_date: Optional[datetime] = Field(default=None, alias="trialStartDate")
    trial_end_date: Optional[datetime] = Field(default=None, alias="trialEndDate")
    start_date: Optional[datetime] = Field(default=None, alias="startDate")
    end_date: Optional[datetime] = Field(default=None, alias="endDate")
    renewal_date: Optional[datetime] = Field(default=None, alias="renewalDate")
    max_students: int = Field(default=500, alias="maxStudents", ge=1)
    storage_limit_gb: int = Field(default=10, alias="storageLimitGb", ge=1)
    enabled_modules: List[str] = Field(default_factory=list, alias="enabledModules")
    billing_cycle: str = Field(default="ANNUALLY", alias="billingCycle")

class OrganizationMetadata(BaseNestedModel):
    naac_grade: Optional[str] = Field(default=None, alias="naacGrade")
    university: Optional[str] = None
    affiliation: Optional[str] = None
    accreditation: Optional[str] = None
    established_year: Optional[int] = Field(default=None, alias="establishedYear", ge=1800, le=2100)
    website: Optional[str] = None
    gst_number: Optional[str] = Field(default=None, alias="gstNumber")
    registration_number: Optional[str] = Field(default=None, alias="registrationNumber")

class University(BaseDocument):
    university_id: str = Field(..., alias="universityId")
    name: str = Field(..., min_length=2, max_length=150)
    code: str = Field(..., min_length=2, max_length=15)
    website: Optional[str] = None

    @field_validator("university_id")
    @classmethod
    def validate_uni_id(cls, v: str) -> str:
        return validate_professional_id(v, "UNI")

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        return v.upper()

    class Settings:
        name = "universities"
        indexes = [
            IndexModel("university_id", unique=True),
            IndexModel("code", unique=True),
        ]

class Organization(BaseDocument):
    organization_id: str = Field(..., alias="organizationId")
    university_id: Optional[PydanticObjectId] = Field(default=None, alias="universityId")
    name: str = Field(..., min_length=2, max_length=100)
    short_name: str = Field(..., alias="shortName", min_length=2, max_length=20)
    slug: str = Field(..., min_length=2, max_length=30)
    description: Optional[str] = Field(default=None, max_length=500)
    logo: Optional[str] = None
    dark_logo: Optional[str] = Field(default=None, alias="darkLogo")
    favicon: Optional[str] = None
    banner: Optional[str] = None
    website: Optional[str] = None
    email_domain: str = Field(..., alias="emailDomain")
    contact_email: EmailStr = Field(..., alias="contactEmail")
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = Field(default=None, alias="postalCode")
    timezone: str = Field(default="UTC")
    currency: str = Field(default="USD")
    language: str = Field(default="en")
    status: OrganizationStatus = Field(default=OrganizationStatus.ACTIVE)
    
    # Nested Future Proof models
    subscription: SubscriptionInfo = Field(default_factory=SubscriptionInfo)
    metadata: OrganizationMetadata = Field(default_factory=OrganizationMetadata)
    
    # Optimization attributes
    search_keywords: List[str] = Field(default_factory=list, alias="searchKeywords")
    normalized_name: Optional[str] = Field(default=None, alias="normalizedName")

    @field_validator("organization_id")
    @classmethod
    def validate_org_id(cls, v: str) -> str:
        return validate_professional_id(v, "ORG")

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError("Slug must contain only lowercase letters, numbers, and hyphens.")
        return v

    @field_validator("email_domain")
    @classmethod
    def validate_email_domain(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Invalid domain suffix format")
        return v.lower()

    class Settings:
        name = "organizations"
        # Disable Beanie's identity map cache so post-soft-delete finds always hit MongoDB
        use_cache = False
        indexes = [
            IndexModel("organizationId", unique=True),
            IndexModel("slug", unique=True),
            IndexModel("emailDomain", unique=True),
            IndexModel("universityId"),
            IndexModel([("name", "text"), ("searchKeywords", "text")]),
        ]

    @classmethod
    def create_draft(cls, org_id: str, name: str, slug: str, domain: str, email: str) -> "Organization":
        """Factory pattern method to initialize draft system organizations."""
        return cls(
            organizationId=org_id,
            name=name,
            shortName=name[:20],
            slug=slug,
            emailDomain=domain,
            contactEmail=email,
            searchKeywords=[name.lower(), slug.lower()],
            normalizedName=name.lower()
        )

class Branding(BaseDocument):
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    primary_color: str = Field(default="#4F46E5", alias="primaryColor")
    secondary_color: str = Field(default="#0891B2", alias="secondaryColor")
    accent_color: str = Field(default="#F59E0B", alias="accentColor")
    surface_color: str = Field(default="#FFFFFF", alias="surfaceColor")
    background_color: str = Field(default="#F9FAFB", alias="backgroundColor")
    dark_mode: bool = Field(default=False, alias="darkMode")
    font_family: str = Field(default="Inter", alias="fontFamily")
    radius: str = Field(default="0.5rem")

    @field_validator("primary_color", "secondary_color", "accent_color", "surface_color", "background_color")
    @classmethod
    def validate_colors(cls, v: str) -> str:
        return validate_hex_color(v)

    class Settings:
        name = "brandings"
        indexes = [
            IndexModel("organization_id", unique=True),
        ]

class OrganizationSettings(BaseDocument):
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    attendance_enabled: bool = Field(default=False, alias="attendanceEnabled")
    certificate_enabled: bool = Field(default=False, alias="certificateEnabled")
    analytics_enabled: bool = Field(default=False, alias="analyticsEnabled")
    club_enabled: bool = Field(default=False, alias="clubEnabled")
    portfolio_enabled: bool = Field(default=False, alias="portfolioEnabled")
    volunteer_enabled: bool = Field(default=False, alias="volunteerEnabled")
    notifications_enabled: bool = Field(default=True, alias="notificationsEnabled")

    class Settings:
        name = "organization_settings"
        indexes = [
            IndexModel("organization_id", unique=True),
        ]
