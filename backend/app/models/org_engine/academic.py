from enum import Enum
from datetime import datetime
from typing import Optional, List
from pymongo import IndexModel
from pydantic import Field, field_validator, model_validator
from beanie import PydanticObjectId

from app.models.base import BaseDocument
from app.models.org_engine.organization import validate_professional_id

class AcademicStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class AcademicYear(BaseDocument):
    academic_year_id: str = Field(..., alias="academicYearId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    name: str = Field(..., min_length=4, max_length=50)  # e.g., "2026-2027"
    start_date: datetime = Field(..., alias="startDate")
    end_date: datetime = Field(..., alias="endDate")
    current: bool = Field(default=False)
    
    # Optimization
    search_keywords: List[str] = Field(default_factory=list, alias="searchKeywords")
    normalized_name: Optional[str] = Field(default=None, alias="normalizedName")

    @field_validator("academic_year_id")
    @classmethod
    def validate_acy_id(cls, v: str) -> str:
        return validate_professional_id(v, "ACY")

    @model_validator(mode="after")
    def validate_dates(self) -> "AcademicYear":
        if self.end_date <= self.start_date:
            raise ValueError("endDate must be chronologically after startDate")
        return self

    class Settings:
        name = "academic_years"
        indexes = [
            IndexModel("academicYearId", unique=True),
            # organizationId + name unique constraint
            IndexModel([("organizationId", 1), ("name", 1)], unique=True),
            IndexModel("organizationId"),
            IndexModel([("name", "text"), ("searchKeywords", "text")]),
        ]

class Semester(BaseDocument):
    semester_id: str = Field(..., alias="semesterId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    academic_year_id: Optional[PydanticObjectId] = Field(default=None, alias="academicYearId")
    number: int = Field(..., ge=1, le=20)
    name: str = Field(..., min_length=2, max_length=50)  # e.g., "Semester 1"
    status: AcademicStatus = Field(default=AcademicStatus.ACTIVE)

    # Optimization
    search_keywords: List[str] = Field(default_factory=list, alias="searchKeywords")
    normalized_name: Optional[str] = Field(default=None, alias="normalizedName")

    @field_validator("semester_id")
    @classmethod
    def validate_sem_id(cls, v: str) -> str:
        return validate_professional_id(v, "SEM")

    class Settings:
        name = "semesters"
        indexes = [
            IndexModel("semesterId", unique=True),
            # organizationId + number unique constraint
            IndexModel([("organizationId", 1), ("number", 1)], unique=True),
            IndexModel("organizationId"),
            IndexModel("academicYearId"),
            IndexModel([("name", "text"), ("searchKeywords", "text")]),
        ]

class Department(BaseDocument):
    department_id: str = Field(..., alias="departmentId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    name: str = Field(..., min_length=2, max_length=100)
    code: str = Field(..., min_length=2, max_length=10)  # e.g., "CSE", "ME"
    hod: Optional[str] = Field(default=None, max_length=100)  # Name or User ID of HOD
    description: Optional[str] = Field(default=None, max_length=500)
    status: AcademicStatus = Field(default=AcademicStatus.ACTIVE)
    
    # Optimization
    search_keywords: List[str] = Field(default_factory=list, alias="searchKeywords")
    normalized_name: Optional[str] = Field(default=None, alias="normalizedName")

    @field_validator("department_id")
    @classmethod
    def validate_dep_id(cls, v: str) -> str:
        return validate_professional_id(v, "DEP")

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        return v.upper()

    class Settings:
        name = "departments"
        indexes = [
            IndexModel("departmentId", unique=True),
            # organizationId + code unique constraint
            IndexModel([("organizationId", 1), ("code", 1)], unique=True),
            IndexModel("organizationId"),
            IndexModel([("name", "text"), ("searchKeywords", "text")]),
        ]

class Branch(BaseDocument):
    branch_id: str = Field(..., alias="branchId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    department_id: PydanticObjectId = Field(..., alias="departmentId")
    code: str = Field(..., min_length=2, max_length=15)  # e.g., "CSE-AI", "CSE-DS"
    name: str = Field(..., min_length=2, max_length=100)
    
    # Optimization
    search_keywords: List[str] = Field(default_factory=list, alias="searchKeywords")
    normalized_name: Optional[str] = Field(default=None, alias="normalizedName")

    @field_validator("branch_id")
    @classmethod
    def validate_brn_id(cls, v: str) -> str:
        return validate_professional_id(v, "BRN")

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        return v.upper()

    class Settings:
        name = "branches"
        indexes = [
            IndexModel("branchId", unique=True),
            IndexModel([("organizationId", 1), ("departmentId", 1), ("code", 1)], unique=True),
            IndexModel("organizationId"),
            IndexModel("departmentId"),
            IndexModel([("name", "text"), ("searchKeywords", "text")]),
        ]


class Section(BaseDocument):
    section_id: str = Field(..., alias="sectionId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    branch_id: PydanticObjectId = Field(..., alias="branchId")
    semester_id: PydanticObjectId = Field(..., alias="semesterId")
    name: str = Field(..., min_length=1, max_length=20)  # e.g., "Section A"
    strength: int = Field(..., ge=1, le=500)  # Maximum students allowed in section
    
    # Optimization
    search_keywords: List[str] = Field(default_factory=list, alias="searchKeywords")
    normalized_name: Optional[str] = Field(default=None, alias="normalizedName")

    @field_validator("section_id")
    @classmethod
    def validate_sec_id(cls, v: str) -> str:
        return validate_professional_id(v, "SEC")

    class Settings:
        name = "sections"
        indexes = [
            IndexModel("sectionId", unique=True),
            IndexModel([("organizationId", 1), ("branchId", 1), ("semesterId", 1), ("name", 1)], unique=True),
            IndexModel("organizationId"),
            IndexModel("branchId"),
            IndexModel("semesterId"),
            IndexModel([("name", "text"), ("searchKeywords", "text")]),
        ]

