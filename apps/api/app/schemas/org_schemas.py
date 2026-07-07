from pydantic import BaseModel, Field, EmailStr, HttpUrl, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from beanie import PydanticObjectId
from zoneinfo import available_timezones
import re

PHONE_REGEX = re.compile(r"^\+?[0-9\s\-()]{7,25}$")
WEBSITE_REGEX = re.compile(r"^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?$")

class BaseCamelSchema(BaseModel):
    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
    }

class SubscriptionInfoResponse(BaseCamelSchema):
    plan: str
    status: str
    trial_start_date: Optional[datetime] = Field(None, alias="trialStartDate")
    trial_end_date: Optional[datetime] = Field(None, alias="trialEndDate")
    start_date: Optional[datetime] = Field(None, alias="startDate")
    end_date: Optional[datetime] = Field(None, alias="endDate")
    renewal_date: Optional[datetime] = Field(None, alias="renewalDate")
    max_students: int = Field(..., alias="maxStudents")
    storage_limit_gb: int = Field(..., alias="storageLimitGb")
    enabled_modules: List[str] = Field(..., alias="enabledModules")
    billing_cycle: str = Field(..., alias="billingCycle")

class OrganizationMetadataResponse(BaseCamelSchema):
    naac_grade: Optional[str] = Field(None, alias="naacGrade")
    university: Optional[str] = None
    affiliation: Optional[str] = None
    accreditation: Optional[str] = None
    established_year: Optional[int] = Field(None, alias="establishedYear")
    website: Optional[str] = None
    gst_number: Optional[str] = Field(None, alias="gstNumber")
    registration_number: Optional[str] = Field(None, alias="registrationNumber")

class OrganizationCreateSchema(BaseCamelSchema):
    organization_id: str = Field(..., alias="organizationId", min_length=10, max_length=30)
    university_id: Optional[str] = Field(default=None, alias="universityId")
    name: str = Field(..., min_length=2, max_length=100)
    short_name: str = Field(..., alias="shortName", min_length=2, max_length=20)
    slug: Optional[str] = Field(default=None, min_length=2, max_length=30)
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

    @field_validator("organization_id")
    @classmethod
    def validate_organization_id(cls, v: str) -> str:
        if not re.match(r"^ORG_[0-9]{6,}$", v):
            raise ValueError("organizationId must follow prefix format: ORG_000001 (min 6 digits)")
        return v

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError("slug must only contain lowercase letters, numbers, and hyphens.")
        return v

    @field_validator("website")
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        if v and not WEBSITE_REGEX.match(v):
            raise ValueError("website URL is not in a valid format (e.g. http://institution.edu).")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v and not PHONE_REGEX.match(v):
            raise ValueError("phone number is invalid.")
        return v

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        if v not in available_timezones():
            raise ValueError("Invalid timezone IANA identifier.")
        return v

    @field_validator("country")
    @classmethod
    def validate_country(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v) < 2:
            raise ValueError("Country identifier must be at least 2 characters long.")
        return v

class OrganizationUpdateSchema(BaseCamelSchema):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    short_name: Optional[str] = Field(None, alias="shortName", min_length=2, max_length=20)
    description: Optional[str] = Field(None, max_length=500)
    logo: Optional[str] = None
    dark_logo: Optional[str] = Field(None, alias="darkLogo")
    favicon: Optional[str] = None
    banner: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = Field(None, alias="postalCode")
    timezone: Optional[str] = None
    currency: Optional[str] = None
    language: Optional[str] = None
    status: Optional[str] = None

    @field_validator("website")
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        if v and not WEBSITE_REGEX.match(v):
            raise ValueError("website URL is not in a valid format.")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v and not PHONE_REGEX.match(v):
            raise ValueError("phone number is invalid.")
        return v

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in available_timezones():
            raise ValueError("Invalid timezone IANA identifier.")
        return v

class OrganizationResponseSchema(BaseCamelSchema):
    id: str = Field(..., alias="id")
    organization_id: str = Field(..., alias="organizationId")
    university_id: Optional[str] = Field(None, alias="universityId")
    name: str
    short_name: str = Field(..., alias="shortName")
    slug: str
    description: Optional[str] = None
    logo: Optional[str] = None
    dark_logo: Optional[str] = Field(None, alias="darkLogo")
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
    postal_code: Optional[str] = Field(None, alias="postalCode")
    timezone: str
    currency: str
    language: str
    status: str
    subscription: SubscriptionInfoResponse
    metadata: OrganizationMetadataResponse
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
    version: int
    revision_number: int = Field(..., alias="revisionNumber")

    @field_validator("id", mode="before")
    @classmethod
    def serialize_object_id(cls, v: Any) -> str:
        # PydanticObjectId is serialized into string automatically
        return str(v)

    @field_validator("university_id", mode="before")
    @classmethod
    def serialize_uni_object_id(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        return str(v)
