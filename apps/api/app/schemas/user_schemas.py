from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from beanie import PydanticObjectId

from apps.api.app.models.identity.user import UserStatus, AccountType
from apps.api.app.schemas.org_schemas import BaseCamelSchema

class ProfileResponseSchema(BaseCamelSchema):
    profile_id: str = Field(..., alias="profileId")
    first_name: str = Field(..., alias="firstName")
    middle_name: Optional[str] = Field(None, alias="middleName")
    last_name: str = Field(..., alias="lastName")
    preferred_name: Optional[str] = Field(None, alias="preferredName")
    avatar: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[datetime] = Field(None, alias="dateOfBirth")
    phone: Optional[str] = None
    alternate_phone: Optional[str] = Field(None, alias="alternatePhone")
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = Field(None, alias="postalCode")
    timezone: str = "UTC"
    language: str = "en"
    bio: Optional[str] = None

class ProfileUpdateSchema(BaseCamelSchema):
    first_name: Optional[str] = Field(None, alias="firstName")
    middle_name: Optional[str] = Field(None, alias="middleName")
    last_name: Optional[str] = Field(None, alias="lastName")
    preferred_name: Optional[str] = Field(None, alias="preferredName")
    gender: Optional[str] = None
    date_of_birth: Optional[datetime] = Field(None, alias="dateOfBirth")
    phone: Optional[str] = None
    alternate_phone: Optional[str] = Field(None, alias="alternatePhone")
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = Field(None, alias="postalCode")
    timezone: Optional[str] = None
    language: Optional[str] = None
    bio: Optional[str] = None

class AcademicAffiliationSchema(BaseCamelSchema):
    roll_number: Optional[str] = Field(None, alias="rollNumber")
    employee_id: Optional[str] = Field(None, alias="employeeId")
    department_id: Optional[str] = Field(None, alias="departmentId")
    program_id: Optional[str] = Field(None, alias="programId")
    branch_id: Optional[str] = Field(None, alias="branchId")
    semester_id: Optional[str] = Field(None, alias="semesterId")
    section_id: Optional[str] = Field(None, alias="sectionId")
    batch: Optional[str] = None
    admission_year: Optional[int] = Field(None, alias="admissionYear")
    graduation_year: Optional[int] = Field(None, alias="graduationYear")
    designation: Optional[str] = None

class UserCreateSchema(BaseCamelSchema):
    username: str = Field(..., min_length=3, max_length=30)
    email: EmailStr
    account_type: AccountType = Field(default=AccountType.STUDENT, alias="accountType")
    first_name: str = Field(..., alias="firstName")
    last_name: str = Field(..., alias="lastName")
    phone: Optional[str] = None
    role_ids: Optional[List[str]] = Field(default=None, alias="roleIds")
    password: Optional[str] = None
    academic_affiliation: Optional[AcademicAffiliationSchema] = Field(default=None, alias="academicAffiliation")

class UserUpdateSchema(BaseCamelSchema):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    status: Optional[UserStatus] = None
    account_type: Optional[AccountType] = Field(None, alias="accountType")
    role_ids: Optional[List[str]] = Field(None, alias="roleIds")
    academic_affiliation: Optional[AcademicAffiliationSchema] = Field(None, alias="academicAffiliation")

class UserResponseSchema(BaseCamelSchema):
    id: str = Field(..., alias="id")
    user_id: str = Field(..., alias="userId")
    organization_id: str = Field(..., alias="organizationId")
    username: str
    email: EmailStr
    status: UserStatus
    account_type: AccountType = Field(..., alias="accountType")
    email_verified: bool = Field(..., alias="emailVerified")
    phone_verified: bool = Field(..., alias="phoneVerified")
    mfa_enabled: bool = Field(..., alias="mfaEnabled")
    profile: Optional[ProfileResponseSchema] = None
    roles: List[str] = Field(default_factory=list)
    academic_affiliation: Optional[AcademicAffiliationSchema] = Field(None, alias="academicAffiliation")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
    last_login: Optional[datetime] = Field(None, alias="lastLogin")

class BulkStatusUpdateSchema(BaseCamelSchema):
    user_ids: List[str] = Field(..., alias="userIds")
    status: UserStatus
    reason: Optional[str] = None

class BulkRolesUpdateSchema(BaseCamelSchema):
    user_ids: List[str] = Field(..., alias="userIds")
    role_ids: List[str] = Field(..., alias="roleIds")
    action: str = Field(..., description="Action to perform: add, remove, or replace")

class ImportRowReport(BaseCamelSchema):
    row_number: int = Field(..., alias="rowNumber")
    username: str
    email: str
    status: str
    errors: List[str] = Field(default_factory=list)

class BulkImportReport(BaseCamelSchema):
    total_processed: int = Field(..., alias="totalProcessed")
    success_count: int = Field(..., alias="successCount")
    failure_count: int = Field(..., alias="failureCount")
    rows: List[ImportRowReport] = Field(default_factory=list)
