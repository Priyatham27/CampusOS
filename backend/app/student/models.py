from datetime import datetime
from typing import List, Optional
from enum import Enum
from pymongo import IndexModel
from pydantic import Field, field_validator, BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from beanie import PydanticObjectId

from app.models.base import BaseDocument
from app.models.org_engine.organization import validate_professional_id

class StudentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"
    GRADUATED = "GRADUATED"
    SUSPENDED = "SUSPENDED"

class DocumentCategory(str, Enum):
    ACADEMIC = "ACADEMIC"
    IDENTITY = "IDENTITY"
    MEDICAL = "MEDICAL"
    OTHER = "OTHER"

class AchievementCategory(str, Enum):
    ACADEMIC = "ACADEMIC"
    SPORTS = "SPORTS"
    CULTURAL = "CULTURAL"
    OTHER = "OTHER"

class SkillLevel(str, Enum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"

class BaseNestedModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        use_enum_values=True,
    )

class EmergencyContact(BaseNestedModel):
    name: str = Field(..., min_length=2, max_length=100)
    relation: str = Field(..., min_length=2, max_length=50)
    phone: str = Field(..., min_length=5, max_length=20)
    alternative_phone: Optional[str] = Field(default=None, alias="alternativePhone")
    email: Optional[str] = Field(default=None)

class StudentPreference(BaseNestedModel):
    notifications_enabled: bool = Field(default=True, alias="notificationsEnabled")
    theme: str = Field(default="light")
    language: str = Field(default="en")

class StudentNote(BaseNestedModel):
    note_id: str = Field(..., alias="noteId")
    author: str = Field(...)
    content: str = Field(...)
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")

class Student(BaseDocument):
    student_id: str = Field(..., alias="studentId")
    user_id: PydanticObjectId = Field(..., alias="userId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    roll_number: str = Field(..., alias="rollNumber", min_length=2, max_length=50)
    
    first_name: str = Field(..., alias="firstName", min_length=1, max_length=100)
    last_name: str = Field(..., alias="lastName", min_length=1, max_length=100)
    email: str = Field(...)
    phone: Optional[str] = Field(default=None)
    date_of_birth: datetime = Field(..., alias="dateOfBirth")
    gender: str = Field(...)
    blood_group: Optional[str] = Field(default=None, alias="bloodGroup")
    admission_date: datetime = Field(default_factory=datetime.utcnow, alias="admissionDate")
    status: StudentStatus = Field(default=StudentStatus.ACTIVE)

    # Academic Affiliation
    academic_year_id: Optional[PydanticObjectId] = Field(default=None, alias="academicYearId")
    department_id: Optional[PydanticObjectId] = Field(default=None, alias="departmentId")
    program_id: Optional[PydanticObjectId] = Field(default=None, alias="programId")
    branch_id: Optional[PydanticObjectId] = Field(default=None, alias="branchId")
    semester_id: Optional[PydanticObjectId] = Field(default=None, alias="semesterId")
    section_id: Optional[PydanticObjectId] = Field(default=None, alias="sectionId")

    # Embedded fields
    emergency_contact: Optional[EmergencyContact] = Field(default=None, alias="emergencyContact")
    preferences: StudentPreference = Field(default_factory=StudentPreference)
    tags: List[str] = Field(default_factory=list)
    notes: List[StudentNote] = Field(default_factory=list)

    # Logical flags
    is_archived: bool = Field(default=False, alias="isArchived")

    @field_validator("student_id")
    @classmethod
    def validate_stu_id(cls, v: str) -> str:
        return validate_professional_id(v, "STU")

    class Settings:
        name = "students"
        indexes = [
            IndexModel("studentId", unique=True),
            IndexModel([("organizationId", 1), ("rollNumber", 1)], unique=True),
            IndexModel("organizationId"),
            IndexModel("userId"),
            IndexModel("academicYearId"),
            IndexModel("semesterId"),
            IndexModel("branchId"),
            IndexModel([("firstName", "text"), ("lastName", "text"), ("email", "text"), ("rollNumber", "text")]),
        ]

class Guardian(BaseDocument):
    guardian_id: str = Field(..., alias="guardianId")
    student_id: PydanticObjectId = Field(..., alias="studentId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    name: str = Field(..., min_length=2, max_length=150)
    relation: str = Field(...)  # e.g., FATHER, MOTHER, GUARDIAN
    phone: str = Field(..., min_length=5, max_length=20)
    email: Optional[str] = Field(default=None)
    occupation: Optional[str] = Field(default=None)
    address: Optional[str] = Field(default=None)
    is_primary: bool = Field(default=False, alias="isPrimary")

    @field_validator("guardian_id")
    @classmethod
    def validate_gua_id(cls, v: str) -> str:
        return validate_professional_id(v, "GUA")

    class Settings:
        name = "guardians"
        indexes = [
            IndexModel("guardianId", unique=True),
            IndexModel("studentId"),
            IndexModel("organizationId"),
        ]

class StudentDocument(BaseDocument):
    document_id: str = Field(..., alias="documentId")
    student_id: PydanticObjectId = Field(..., alias="studentId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    name: str = Field(..., min_length=2, max_length=150)
    file_path: str = Field(..., alias="filePath")
    file_type: str = Field(..., alias="fileType")  # e.g., PDF, PNG, JPG
    file_size: int = Field(..., alias="fileSize")  # In bytes
    uploaded_at: datetime = Field(default_factory=datetime.utcnow, alias="uploadedAt")
    category: DocumentCategory = Field(default=DocumentCategory.ACADEMIC)
    is_verified: bool = Field(default=False, alias="isVerified")

    @field_validator("document_id")
    @classmethod
    def validate_doc_id(cls, v: str) -> str:
        return validate_professional_id(v, "DOC")

    class Settings:
        name = "student_documents"
        indexes = [
            IndexModel("documentId", unique=True),
            IndexModel("studentId"),
            IndexModel("organizationId"),
        ]

class StudentAchievement(BaseDocument):
    achievement_id: str = Field(..., alias="achievementId")
    student_id: PydanticObjectId = Field(..., alias="studentId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    title: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = Field(default=None)
    date_earned: datetime = Field(..., alias="dateEarned")
    category: AchievementCategory = Field(default=AchievementCategory.ACADEMIC)
    certificate_path: Optional[str] = Field(default=None, alias="certificatePath")

    @field_validator("achievement_id")
    @classmethod
    def validate_ach_id(cls, v: str) -> str:
        return validate_professional_id(v, "ACH")

    class Settings:
        name = "student_achievements"
        indexes = [
            IndexModel("achievementId", unique=True),
            IndexModel("studentId"),
            IndexModel("organizationId"),
        ]

class StudentSkill(BaseDocument):
    skill_id: str = Field(..., alias="skillId")
    student_id: PydanticObjectId = Field(..., alias="studentId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    name: str = Field(..., min_length=1, max_length=100)
    level: SkillLevel = Field(default=SkillLevel.BEGINNER)
    verified: bool = Field(default=False)

    @field_validator("skill_id")
    @classmethod
    def validate_skl_id(cls, v: str) -> str:
        return validate_professional_id(v, "SKL")

    class Settings:
        name = "student_skills"
        indexes = [
            IndexModel("skillId", unique=True),
            IndexModel("studentId"),
            IndexModel("organizationId"),
            IndexModel([("studentId", 1), ("name", 1)], unique=True),
        ]

STUDENT_MODELS = [
    Student,
    Guardian,
    StudentDocument,
    StudentAchievement,
    StudentSkill
]
