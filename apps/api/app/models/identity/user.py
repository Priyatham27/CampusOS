from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pymongo import IndexModel
from pydantic import Field, EmailStr, field_validator, model_validator
from beanie import PydanticObjectId
import re
from zoneinfo import available_timezones

from apps.api.app.models.base import BaseDocument
from apps.api.app.models.org_engine.organization import validate_professional_id

PHONE_REGEX = re.compile(r"^\+?[0-9\s\-()]{7,25}$")
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.]{3,30}$")

class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    LOCKED = "LOCKED"

class AccountType(str, Enum):
    STUDENT = "STUDENT"
    FACULTY = "FACULTY"
    ADMIN = "ADMIN"
    SUPERADMIN = "SUPERADMIN"
    SUPPORT = "SUPPORT"
    VOLUNTEER = "VOLUNTEER"

class StudentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    ALUMNI = "ALUMNI"
    WITHDRAWN = "WITHDRAWN"

class FacultyStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ON_LEAVE = "ON_LEAVE"
    RESIGNED = "RESIGNED"
    RETIRED = "RETIRED"

class User(BaseDocument):
    user_id: str = Field(..., alias="userId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    username: str = Field(..., min_length=3, max_length=30)
    email: EmailStr = Field(...)
    password_hash: str = Field(..., alias="passwordHash")
    status: UserStatus = Field(default=UserStatus.ACTIVE)
    account_type: AccountType = Field(default=AccountType.STUDENT, alias="accountType")
    email_verified: bool = Field(default=False, alias="emailVerified")
    phone_verified: bool = Field(default=False, alias="phoneVerified")
    mfa_enabled: bool = Field(default=False, alias="mfaEnabled")
    profile_id: Optional[PydanticObjectId] = Field(default=None, alias="profileId")
    last_login: Optional[datetime] = Field(default=None, alias="lastLogin")
    failed_login_attempts: int = Field(default=0, alias="failedLoginAttempts")
    locked_until: Optional[datetime] = Field(default=None, alias="lockedUntil")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("user_id")
    @classmethod
    def validate_usr_id(cls, v: str) -> str:
        return validate_professional_id(v, "USR")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not USERNAME_REGEX.match(v):
            raise ValueError("Username must be 3-30 characters and can only contain alphanumeric characters, underscores, hyphens, and periods.")
        return v.lower()

    @field_validator("email")
    @classmethod
    def validate_email_lower(cls, v: EmailStr) -> EmailStr:
        return v.lower()

    class Settings:
        name = "users"
        indexes = [
            IndexModel("userId", unique=True),
            IndexModel([("organizationId", 1), ("username", 1)], unique=True),
            IndexModel("email", unique=True),
            IndexModel("organizationId"),
            IndexModel("status"),
        ]

class Profile(BaseDocument):
    profile_id: str = Field(..., alias="profileId")
    user_id: PydanticObjectId = Field(..., alias="userId")
    first_name: str = Field(..., alias="firstName", min_length=1, max_length=50)
    middle_name: Optional[str] = Field(default=None, alias="middleName", max_length=50)
    last_name: str = Field(..., alias="lastName", min_length=1, max_length=50)
    preferred_name: Optional[str] = Field(default=None, alias="preferredName", max_length=100)
    avatar: Optional[str] = Field(default=None)
    gender: Optional[str] = Field(default=None, max_length=20)
    date_of_birth: Optional[datetime] = Field(default=None, alias="dateOfBirth")
    phone: Optional[str] = Field(default=None)
    alternate_phone: Optional[str] = Field(default=None, alias="alternatePhone")
    address: Optional[str] = Field(default=None, max_length=250)
    city: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=100)
    postal_code: Optional[str] = Field(default=None, alias="postalCode", max_length=20)
    timezone: str = Field(default="UTC")
    language: str = Field(default="en", max_length=10)
    bio: Optional[str] = Field(default=None, max_length=500)

    @field_validator("profile_id")
    @classmethod
    def validate_prf_id(cls, v: str) -> str:
        return validate_professional_id(v, "PRF")

    @field_validator("phone", "alternate_phone")
    @classmethod
    def validate_phone_number(cls, v: Optional[str]) -> Optional[str]:
        if v and not PHONE_REGEX.match(v):
            raise ValueError("Phone number must be a valid telephone format (7-25 characters).")
        return v

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        if v not in available_timezones():
            raise ValueError("Invalid timezone IANA identifier.")
        return v

    class Settings:
        name = "profiles"
        indexes = [
            IndexModel("profileId", unique=True),
            IndexModel("userId", unique=True),
        ]

class StudentProfile(BaseDocument):
    student_profile_id: str = Field(default_factory=lambda: "STD_000000", alias="studentProfileId")
    user_id: PydanticObjectId = Field(..., alias="userId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    roll_number: str = Field(..., alias="rollNumber", min_length=2, max_length=30)
    department_id: PydanticObjectId = Field(..., alias="departmentId")
    program_id: PydanticObjectId = Field(..., alias="programId")
    branch_id: PydanticObjectId = Field(..., alias="branchId")
    semester_id: PydanticObjectId = Field(..., alias="semesterId")
    section_id: PydanticObjectId = Field(..., alias="sectionId")
    batch: str = Field(..., min_length=2, max_length=20)  # e.g., "2026-2030"
    admission_year: int = Field(..., alias="admissionYear", ge=2000, le=2100)
    graduation_year: int = Field(..., alias="graduationYear", ge=2000, le=2100)
    student_status: StudentStatus = Field(default=StudentStatus.ACTIVE, alias="studentStatus")

    @field_validator("student_profile_id")
    @classmethod
    def validate_std_id(cls, v: str) -> str:
        # Allow default factory trigger or validate
        if v == "STD_000000":
            return v
        return validate_professional_id(v, "STD")

    @model_validator(mode="after")
    def validate_years(self) -> "StudentProfile":
        if self.graduation_year < self.admission_year:
            raise ValueError("graduationYear must be chronologically after or equal to admissionYear")
        return self

    class Settings:
        name = "student_profiles"
        indexes = [
            IndexModel("studentProfileId", unique=True),
            IndexModel("userId", unique=True),
            IndexModel([("organizationId", 1), ("rollNumber", 1)], unique=True),
            IndexModel("organizationId"),
            IndexModel("departmentId"),
            IndexModel("programId"),
        ]

class FacultyProfile(BaseDocument):
    faculty_profile_id: str = Field(default_factory=lambda: "FAC_000000", alias="facultyProfileId")
    user_id: PydanticObjectId = Field(..., alias="userId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    employee_id: str = Field(..., alias="employeeId", min_length=2, max_length=30)
    designation: str = Field(..., min_length=2, max_length=100)
    department_id: PydanticObjectId = Field(..., alias="departmentId")
    joining_date: datetime = Field(..., alias="joiningDate")
    qualification: str = Field(..., min_length=2, max_length=150)
    office_location: Optional[str] = Field(default=None, alias="officeLocation", max_length=100)
    status: FacultyStatus = Field(default=FacultyStatus.ACTIVE)

    @field_validator("faculty_profile_id")
    @classmethod
    def validate_fac_id(cls, v: str) -> str:
        if v == "FAC_000000":
            return v
        return validate_professional_id(v, "FAC")

    class Settings:
        name = "faculty_profiles"
        indexes = [
            IndexModel("facultyProfileId", unique=True),
            IndexModel("userId", unique=True),
            IndexModel([("organizationId", 1), ("employeeId", 1)], unique=True),
            IndexModel("organizationId"),
            IndexModel("departmentId"),
        ]

class AdminProfile(BaseDocument):
    admin_profile_id: str = Field(default_factory=lambda: "ADM_000000", alias="adminProfileId")
    user_id: PydanticObjectId = Field(..., alias="userId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    designation: str = Field(..., min_length=2, max_length=100)
    notes: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("admin_profile_id")
    @classmethod
    def validate_adm_id(cls, v: str) -> str:
        if v == "ADM_000000":
            return v
        return validate_professional_id(v, "ADM")

    class Settings:
        name = "admin_profiles"
        indexes = [
            IndexModel("adminProfileId", unique=True),
            IndexModel("userId", unique=True),
            IndexModel("organizationId"),
        ]
