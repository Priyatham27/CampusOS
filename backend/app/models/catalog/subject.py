from enum import Enum
from typing import List, Optional
from pymongo import IndexModel
from pydantic import BaseModel, Field, field_validator, model_validator
from beanie import PydanticObjectId

from app.models.base import BaseDocument
from app.models.org_engine.organization import validate_professional_id


class SubjectType(str, Enum):
    CORE = "CORE"
    ELECTIVE = "ELECTIVE"
    LAB = "LAB"
    PROJECT = "PROJECT"
    SEMINAR = "SEMINAR"


class BloomLevel(str, Enum):
    REMEMBER = "REMEMBER"
    UNDERSTAND = "UNDERSTAND"
    APPLY = "APPLY"
    ANALYZE = "ANALYZE"
    EVALUATE = "EVALUATE"
    CREATE = "CREATE"


class LearningOutcome(BaseModel):
    """Embedded learning outcome using Bloom's taxonomy."""
    code: str = Field(..., min_length=1, max_length=20)       # e.g., "LO1"
    description: str = Field(..., min_length=5, max_length=500)
    bloom_level: BloomLevel = Field(..., alias="bloomLevel")

    model_config = {"populate_by_name": True, "use_enum_values": True}


class AssessmentComponent(BaseModel):
    """A single graded component within an assessment scheme."""
    component: str = Field(..., min_length=1, max_length=100)  # e.g., "Mid-Term Exam"
    weight: float = Field(..., gt=0.0, le=100.0)               # percentage weight
    max_marks: int = Field(..., ge=1, le=1000, alias="maxMarks")

    model_config = {"populate_by_name": True}


class AssessmentScheme(BaseModel):
    """
    Embedded assessment scheme with mandatory 100% weight validation.
    All component weights MUST sum to exactly 100.0.
    """
    components: List[AssessmentComponent] = Field(..., min_length=1)
    passing_percentage: float = Field(..., ge=1.0, le=100.0, alias="passingPercentage")

    @model_validator(mode="after")
    def validate_weights_sum(self) -> "AssessmentScheme":
        total = sum(c.weight for c in self.components)
        # Allow tiny floating point imprecision (±0.01)
        if abs(total - 100.0) > 0.01:
            raise ValueError(
                f"Assessment component weights must sum to exactly 100%. "
                f"Current total: {total:.2f}%"
            )
        return self

    model_config = {"populate_by_name": True}


class Subject(BaseDocument):
    """
    A single subject (course unit) within a Curriculum.
    
    Key invariants:
    - prerequisites must be subject_ids within the same curriculum
    - no prerequisite cycles allowed (enforced at service layer via DFS)
    - assessment_scheme weights must sum to 100% (enforced by embedded validator)
    """
    subject_id: str = Field(..., alias="subjectId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    curriculum_id: PydanticObjectId = Field(..., alias="curriculumId")

    semester_number: int = Field(..., ge=1, le=20, alias="semesterNumber")
    subject_code: str = Field(..., min_length=2, max_length=20, alias="subjectCode")
    name: str = Field(..., min_length=2, max_length=150)
    credits: float = Field(..., ge=0.5, le=30.0)
    subject_type: SubjectType = Field(default=SubjectType.CORE, alias="subjectType")

    # Elective grouping
    is_elective: bool = Field(default=False, alias="isElective")
    elective_group: Optional[str] = Field(default=None, max_length=100, alias="electiveGroup")

    # Prerequisite list — stores subject_id strings (not ObjectIds) for graph operations
    prerequisites: List[str] = Field(default_factory=list)

    # Embedded curriculum-specific data
    learning_outcomes: List[LearningOutcome] = Field(default_factory=list, alias="learningOutcomes")
    assessment_scheme: Optional[AssessmentScheme] = Field(default=None, alias="assessmentScheme")

    # Optimization
    search_keywords: List[str] = Field(default_factory=list, alias="searchKeywords")
    normalized_name: Optional[str] = Field(default=None, alias="normalizedName")

    @field_validator("subject_id")
    @classmethod
    def validate_sub_id(cls, v: str) -> str:
        return validate_professional_id(v, "SUB")

    @field_validator("subject_code")
    @classmethod
    def validate_subject_code(cls, v: str) -> str:
        return v.upper()

    @model_validator(mode="after")
    def validate_elective_group(self) -> "Subject":
        if self.is_elective and not self.elective_group:
            raise ValueError("isElective=True requires an electiveGroup to be specified.")
        return self

    class Settings:
        name = "subjects"
        indexes = [
            IndexModel("subjectId", unique=True),
            # Subject code must be unique within a curriculum
            IndexModel(
                [("curriculumId", 1), ("subjectCode", 1)],
                unique=True
            ),
            IndexModel("organizationId"),
            IndexModel("curriculumId"),
            IndexModel("semesterNumber"),
            IndexModel("subjectType"),
            IndexModel([("name", "text"), ("subjectCode", "text"), ("searchKeywords", "text")]),
        ]
