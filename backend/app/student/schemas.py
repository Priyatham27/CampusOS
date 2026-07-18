from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from pydantic.alias_generators import to_camel

class BaseSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        use_enum_values=True
    )

class EmergencyContactSchema(BaseSchema):
    name: str = Field(..., min_length=2, max_length=100)
    relation: str = Field(..., min_length=2, max_length=50)
    phone: str = Field(..., min_length=5, max_length=20)
    alternative_phone: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)

class StudentPreferenceSchema(BaseSchema):
    notifications_enabled: bool = Field(default=True)
    theme: str = Field(default="light")
    language: str = Field(default="en")

class StudentNoteCreateSchema(BaseSchema):
    content: str = Field(..., min_length=1)

class StudentNoteResponseSchema(BaseSchema):
    note_id: str
    author: str
    content: str
    created_at: datetime

class StudentCreateSchema(BaseSchema):
    roll_number: str = Field(..., min_length=2, max_length=50)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr = Field(...)
    phone: Optional[str] = Field(default=None)
    date_of_birth: str = Field(...)  # ISO format string
    gender: str = Field(..., min_length=1)
    blood_group: Optional[str] = Field(default=None)
    admission_date: Optional[str] = Field(default=None)
    
    academic_year_id: Optional[str] = Field(default=None)
    department_id: Optional[str] = Field(default=None)
    program_id: Optional[str] = Field(default=None)
    branch_id: Optional[str] = Field(default=None)
    semester_id: Optional[str] = Field(default=None)
    section_id: Optional[str] = Field(default=None)

    emergency_contact: Optional[EmergencyContactSchema] = Field(default=None)
    tags: List[str] = Field(default_factory=list)

class StudentUpdateSchema(BaseSchema):
    first_name: Optional[str] = Field(default=None)
    last_name: Optional[str] = Field(default=None)
    phone: Optional[str] = Field(default=None)
    date_of_birth: Optional[str] = Field(default=None)
    gender: Optional[str] = Field(default=None)
    blood_group: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default=None)

    academic_year_id: Optional[str] = Field(default=None)
    department_id: Optional[str] = Field(default=None)
    program_id: Optional[str] = Field(default=None)
    branch_id: Optional[str] = Field(default=None)
    semester_id: Optional[str] = Field(default=None)
    section_id: Optional[str] = Field(default=None)

    emergency_contact: Optional[EmergencyContactSchema] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)

class StudentResponseSchema(BaseSchema):
    id: str
    student_id: str
    user_id: str
    organization_id: str
    roll_number: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str]
    date_of_birth: datetime
    gender: str
    blood_group: Optional[str]
    admission_date: datetime
    status: str
    is_archived: bool

    academic_year_id: Optional[str] = None
    department_id: Optional[str] = None
    program_id: Optional[str] = None
    branch_id: Optional[str] = None
    semester_id: Optional[str] = None
    section_id: Optional[str] = None

    emergency_contact: Optional[EmergencyContactSchema] = None
    preferences: StudentPreferenceSchema
    tags: List[str] = []
    notes: List[StudentNoteResponseSchema] = []

class GuardianCreateUpdateSchema(BaseSchema):
    name: str = Field(..., min_length=2, max_length=150)
    relation: str = Field(..., min_length=2)
    phone: str = Field(..., min_length=5, max_length=20)
    email: Optional[EmailStr] = Field(default=None)
    occupation: Optional[str] = Field(default=None)
    address: Optional[str] = Field(default=None)
    is_primary: bool = Field(default=False)

class GuardianResponseSchema(BaseSchema):
    id: str
    guardian_id: str
    student_id: str
    organization_id: str
    name: str
    relation: str
    phone: str
    email: Optional[str]
    occupation: Optional[str]
    address: Optional[str]
    is_primary: bool

class DocumentCreateSchema(BaseSchema):
    name: str = Field(..., min_length=2, max_length=150)
    file_path: str = Field(..., min_length=1)
    file_type: str = Field(..., min_length=1)
    file_size: int = Field(..., ge=0)
    category: str = Field(default="ACADEMIC")

class DocumentResponseSchema(BaseSchema):
    id: str
    document_id: str
    student_id: str
    organization_id: str
    name: str
    file_path: str
    file_type: str
    file_size: int
    uploaded_at: datetime
    category: str
    is_verified: bool

class AchievementCreateSchema(BaseSchema):
    title: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = Field(default=None)
    date_earned: str = Field(...)  # ISO format string
    category: str = Field(default="ACADEMIC")
    certificate_path: Optional[str] = Field(default=None)

class AchievementResponseSchema(BaseSchema):
    id: str
    achievement_id: str
    student_id: str
    organization_id: str
    title: str
    description: Optional[str]
    date_earned: datetime
    category: str
    certificate_path: Optional[str]

class SkillCreateSchema(BaseSchema):
    name: str = Field(..., min_length=1, max_length=100)
    level: str = Field(default="BEGINNER")

class SkillResponseSchema(BaseSchema):
    id: str
    skill_id: str
    student_id: str
    organization_id: str
    name: str
    level: str
    verified: bool

class BulkImportRowSchema(BaseSchema):
    roll_number: str
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    date_of_birth: str
    gender: str
    blood_group: Optional[str] = None
    admission_date: Optional[str] = None

class BulkImportSchema(BaseSchema):
    records: List[BulkImportRowSchema]
