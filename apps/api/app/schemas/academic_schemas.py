from pydantic import BaseModel, Field, ConfigDict, BeforeValidator
from datetime import datetime
from typing import Optional, List, Any
from typing_extensions import Annotated
from apps.api.app.models.org_engine.academic import AcademicStatus
from apps.api.app.models.org_engine.curriculum import ProgramLevel

# Annotated validator to stringify MongoDB ObjectIDs before validation runs
PyObjectIdStr = Annotated[str, BeforeValidator(lambda v: str(v) if v is not None else None)]

# Helper config
schema_config = ConfigDict(
    populate_by_name=True,
    from_attributes=True,
    use_enum_values=True
)

# ==========================================
# ACADEMIC YEARS
# ==========================================

class AcademicYearCreateSchema(BaseModel):
    name: str = Field(..., min_length=4, max_length=50)
    startDate: datetime = Field(..., alias="startDate")
    endDate: datetime = Field(..., alias="endDate")
    current: bool = Field(default=False)
    model_config = schema_config

class AcademicYearUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, min_length=4, max_length=50)
    startDate: Optional[datetime] = Field(None, alias="startDate")
    endDate: Optional[datetime] = Field(None, alias="endDate")
    current: Optional[bool] = Field(None)
    model_config = schema_config

class AcademicYearResponseSchema(BaseModel):
    id: PyObjectIdStr = Field(..., alias="id")
    academic_year_id: str = Field(..., alias="academicYearId")
    organization_id: PyObjectIdStr = Field(..., alias="organizationId")
    name: str
    start_date: datetime = Field(..., alias="startDate")
    end_date: datetime = Field(..., alias="endDate")
    current: bool
    model_config = schema_config

# ==========================================
# DEPARTMENTS
# ==========================================

class DepartmentCreateSchema(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    code: str = Field(..., min_length=2, max_length=10)
    hod: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    status: AcademicStatus = Field(default=AcademicStatus.ACTIVE)
    model_config = schema_config

class DepartmentUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    code: Optional[str] = Field(None, min_length=2, max_length=10)
    hod: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    status: Optional[AcademicStatus] = Field(None)
    model_config = schema_config

class DepartmentResponseSchema(BaseModel):
    id: PyObjectIdStr = Field(..., alias="id")
    department_id: str = Field(..., alias="departmentId")
    organization_id: PyObjectIdStr = Field(..., alias="organizationId")
    name: str
    code: str
    hod: Optional[str] = None
    description: Optional[str] = None
    status: AcademicStatus
    model_config = schema_config

# ==========================================
# PROGRAMS
# ==========================================

class ProgramCreateSchema(BaseModel):
    departmentId: str = Field(..., alias="departmentId")
    name: str = Field(..., min_length=2, max_length=150)
    duration: int = Field(..., ge=1, le=10)
    level: ProgramLevel = Field(default=ProgramLevel.UNDERGRADUATE)
    model_config = schema_config

class ProgramUpdateSchema(BaseModel):
    departmentId: Optional[str] = Field(None, alias="departmentId")
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    duration: Optional[int] = Field(None, ge=1, le=10)
    level: Optional[ProgramLevel] = Field(None)
    model_config = schema_config

class ProgramResponseSchema(BaseModel):
    id: PyObjectIdStr = Field(..., alias="id")
    program_id: str = Field(..., alias="programId")
    organization_id: PyObjectIdStr = Field(..., alias="organizationId")
    department_id: PyObjectIdStr = Field(..., alias="departmentId")
    name: str
    duration: int
    level: ProgramLevel
    model_config = schema_config

# ==========================================
# BRANCHES
# ==========================================

class BranchCreateSchema(BaseModel):
    departmentId: str = Field(..., alias="departmentId")
    code: str = Field(..., min_length=2, max_length=15)
    name: str = Field(..., min_length=2, max_length=100)
    model_config = schema_config

class BranchUpdateSchema(BaseModel):
    departmentId: Optional[str] = Field(None, alias="departmentId")
    code: Optional[str] = Field(None, min_length=2, max_length=15)
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    model_config = schema_config

class BranchResponseSchema(BaseModel):
    id: PyObjectIdStr = Field(..., alias="id")
    branch_id: str = Field(..., alias="branchId")
    organization_id: PyObjectIdStr = Field(..., alias="organizationId")
    department_id: PyObjectIdStr = Field(..., alias="departmentId")
    code: str
    name: str
    model_config = schema_config

# ==========================================
# SEMESTERS
# ==========================================

class SemesterCreateSchema(BaseModel):
    number: int = Field(..., ge=1, le=20)
    name: str = Field(..., min_length=2, max_length=50)
    status: AcademicStatus = Field(default=AcademicStatus.ACTIVE)
    model_config = schema_config

class SemesterUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    status: Optional[AcademicStatus] = Field(None)
    model_config = schema_config

class SemesterResponseSchema(BaseModel):
    id: PyObjectIdStr = Field(..., alias="id")
    semester_id: str = Field(..., alias="semesterId")
    organization_id: PyObjectIdStr = Field(..., alias="organizationId")
    number: int
    name: str
    status: AcademicStatus
    model_config = schema_config

# ==========================================
# SECTIONS
# ==========================================

class SectionCreateSchema(BaseModel):
    branchId: str = Field(..., alias="branchId")
    semesterId: str = Field(..., alias="semesterId")
    name: str = Field(..., min_length=1, max_length=20)
    strength: int = Field(..., ge=1, le=500)
    model_config = schema_config

class SectionUpdateSchema(BaseModel):
    branchId: Optional[str] = Field(None, alias="branchId")
    semesterId: Optional[str] = Field(None, alias="semesterId")
    name: Optional[str] = Field(None, min_length=1, max_length=20)
    strength: Optional[int] = Field(None, ge=1, le=500)
    model_config = schema_config

class SectionResponseSchema(BaseModel):
    id: PyObjectIdStr = Field(..., alias="id")
    section_id: str = Field(..., alias="sectionId")
    organization_id: PyObjectIdStr = Field(..., alias="organizationId")
    branch_id: PyObjectIdStr = Field(..., alias="branchId")
    semester_id: PyObjectIdStr = Field(..., alias="semesterId")
    name: str
    strength: int
    model_config = schema_config

# ==========================================
# COURSES
# ==========================================

class CourseCreateSchema(BaseModel):
    programId: str = Field(..., alias="programId")
    courseCode: str = Field(..., alias="courseCode", min_length=2, max_length=15)
    credits: float = Field(..., ge=0.5, le=30.0)
    semester: str = Field(..., min_length=1, max_length=30)
    model_config = schema_config

class CourseUpdateSchema(BaseModel):
    programId: Optional[str] = Field(None, alias="programId")
    courseCode: Optional[str] = Field(None, min_length=2, max_length=15)
    credits: Optional[float] = Field(None, ge=0.5, le=30.0)
    semester: Optional[str] = Field(None, min_length=1, max_length=30)
    model_config = schema_config

class CourseResponseSchema(BaseModel):
    id: PyObjectIdStr = Field(..., alias="id")
    course_id: str = Field(..., alias="courseId")
    organization_id: PyObjectIdStr = Field(..., alias="organizationId")
    program_id: PyObjectIdStr = Field(..., alias="programId")
    course_code: str = Field(..., alias="courseCode")
    credits: float
    semester: str
    model_config = schema_config

# ==========================================
# BULK PAYLOAD SCHEMAS
# ==========================================

class BulkDeletePayload(BaseModel):
    ids: List[str]
    model_config = schema_config

class DepartmentBulkUpdateSchema(BaseModel):
    departmentId: str = Field(..., alias="departmentId")
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    code: Optional[str] = Field(None, min_length=2, max_length=10)
    hod: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    status: Optional[AcademicStatus] = Field(None)
    model_config = schema_config

class ProgramBulkUpdateSchema(BaseModel):
    programId: str = Field(..., alias="programId")
    departmentId: Optional[str] = Field(None, alias="departmentId")
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    duration: Optional[int] = Field(None, ge=1, le=10)
    level: Optional[ProgramLevel] = Field(None)
    model_config = schema_config

class BranchBulkUpdateSchema(BaseModel):
    branchId: str = Field(..., alias="branchId")
    departmentId: Optional[str] = Field(None, alias="departmentId")
    code: Optional[str] = Field(None, min_length=2, max_length=15)
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    model_config = schema_config

class SectionBulkUpdateSchema(BaseModel):
    sectionId: str = Field(..., alias="sectionId")
    branchId: Optional[str] = Field(None, alias="branchId")
    semesterId: Optional[str] = Field(None, alias="semesterId")
    name: Optional[str] = Field(None, min_length=1, max_length=20)
    strength: Optional[int] = Field(None, ge=1, le=500)
    model_config = schema_config

class CourseBulkUpdateSchema(BaseModel):
    courseId: str = Field(..., alias="courseId")
    programId: Optional[str] = Field(None, alias="programId")
    courseCode: Optional[str] = Field(None, min_length=2, max_length=15)
    credits: Optional[float] = Field(None, ge=0.5, le=30.0)
    semester: Optional[str] = Field(None, min_length=1, max_length=30)
    model_config = schema_config

