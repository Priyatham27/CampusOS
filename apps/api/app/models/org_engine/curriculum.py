from enum import Enum
from typing import List, Optional
from pymongo import IndexModel
from pydantic import Field, field_validator
from beanie import PydanticObjectId

from apps.api.app.models.base import BaseDocument
from apps.api.app.models.org_engine.organization import validate_professional_id

class ProgramLevel(str, Enum):
    UNDERGRADUATE = "UNDERGRADUATE"
    POSTGRADUATE = "POSTGRADUATE"
    DOCTORATE = "DOCTORATE"
    DIPLOMA = "DIPLOMA"

class Program(BaseDocument):
    program_id: str = Field(..., alias="programId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    department_id: PydanticObjectId = Field(..., alias="departmentId")
    name: str = Field(..., min_length=2, max_length=150)  # e.g., "Bachelor of Technology"
    duration: int = Field(..., ge=1, le=10)  # Number of years
    level: ProgramLevel = Field(default=ProgramLevel.UNDERGRADUATE)
    
    # Optimization
    search_keywords: List[str] = Field(default_factory=list, alias="searchKeywords")
    normalized_name: Optional[str] = Field(default=None, alias="normalizedName")

    @field_validator("program_id")
    @classmethod
    def validate_prg_id(cls, v: str) -> str:
        return validate_professional_id(v, "PRG")

    class Settings:
        name = "programs"
        indexes = [
            IndexModel("programId", unique=True),
            # organizationId + departmentId + name unique constraint
            IndexModel([("organizationId", 1), ("departmentId", 1), ("name", 1)], unique=True),
            IndexModel("organizationId"),
            IndexModel("departmentId"),
            IndexModel([("name", "text"), ("searchKeywords", "text")]),
        ]

class Course(BaseDocument):
    course_id: str = Field(..., alias="courseId")
    program_id: PydanticObjectId = Field(..., alias="programId")
    course_code: str = Field(..., alias="courseCode", min_length=2, max_length=15)  # e.g., "CS101"
    credits: float = Field(..., ge=0.5, le=30.0)  # Course credit hours weight
    semester: str = Field(..., min_length=1, max_length=30)  # semester string reference
    
    # Optimization
    search_keywords: List[str] = Field(default_factory=list, alias="searchKeywords")
    normalized_name: Optional[str] = Field(default=None, alias="normalizedName")

    @field_validator("course_id")
    @classmethod
    def validate_course_id(cls, v: str) -> str:
        return validate_professional_id(v, "COURSE")

    @field_validator("course_code")
    @classmethod
    def validate_course_code(cls, v: str) -> str:
        return v.upper()

    class Settings:
        name = "courses"
        indexes = [
            IndexModel("courseId", unique=True),
            # programId + courseCode unique constraint
            IndexModel([("programId", 1), ("courseCode", 1)], unique=True),
            IndexModel("programId"),
            IndexModel([("courseCode", "text"), ("searchKeywords", "text")]),
        ]
