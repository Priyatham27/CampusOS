from enum import Enum
from datetime import datetime
from typing import List, Optional
from pymongo import IndexModel
from pydantic import Field, field_validator
from beanie import PydanticObjectId

from app.models.base import BaseDocument
from app.models.org_engine.organization import validate_professional_id


class CurriculumStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class Curriculum(BaseDocument):
    """
    Versioned academic curriculum document.
    
    Lifecycle: DRAFT → ACTIVE → ARCHIVED
    Non-destructive versioning: clone creates a new DRAFT with version+1.
    Students admitted under a version remain pinned to that version forever.
    """
    curriculum_id: str = Field(..., alias="curriculumId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    program_id: PydanticObjectId = Field(..., alias="programId")

    name: str = Field(..., min_length=2, max_length=200)  # e.g., "B.Tech CSE 2024 Curriculum"
    version: int = Field(default=1, ge=1)
    status: CurriculumStatus = Field(default=CurriculumStatus.DRAFT)

    effective_from: datetime = Field(default_factory=datetime.utcnow, alias="effectiveFrom")
    total_credits: float = Field(default=0.0, ge=0.0, alias="totalCredits")
    description: Optional[str] = Field(default=None, max_length=1000)

    # Version lineage — set on clone operations
    parent_curriculum_id: Optional[PydanticObjectId] = Field(default=None, alias="parentCurriculumId")

    # Cohort pinning — e.g., "2024-28" identifies which batch of students uses this version
    admission_batch: Optional[str] = Field(default=None, max_length=20, alias="admissionBatch")

    # Optimization
    search_keywords: List[str] = Field(default_factory=list, alias="searchKeywords")
    normalized_name: Optional[str] = Field(default=None, alias="normalizedName")

    @field_validator("curriculum_id")
    @classmethod
    def validate_curr_id(cls, v: str) -> str:
        return validate_professional_id(v, "CURR")

    class Settings:
        name = "curricula"
        indexes = [
            IndexModel("curriculumId", unique=True),
            # An organization can have multiple curricula per program (versioned)
            # but name+version must be unique within an org
            IndexModel(
                [("organizationId", 1), ("programId", 1), ("version", 1)],
                unique=True
            ),
            IndexModel("organizationId"),
            IndexModel("programId"),
            IndexModel("status"),
            IndexModel("parentCurriculumId"),
            IndexModel([("name", "text"), ("searchKeywords", "text")]),
        ]
