"""
Catalog Bounded Context — CampusOS Platform
===========================================
The Academic Catalog Engine is the canonical source of truth for
curriculum data: versioned curricula, subjects, prerequisites,
learning outcomes, and assessment schemes.

External contexts (Student, Faculty, Events, Grading) MUST consume
curriculum data through this module's public interfaces.

Public surface:
    - CurriculumService
    - SubjectService
    - CatalogService
    - CatalogException hierarchy
"""

from app.catalog.exceptions import (
    CatalogException,
    CurriculumNotFound,
    DuplicateCurriculum,
    CurriculumStatusConflict,
    CurriculumImmutable,
    SubjectNotFound,
    DuplicateSubject,
    PrerequisiteCycleDetected,
    PrerequisiteNotFound,
    PrerequisiteInUse,
    AssessmentSchemeInvalid,
)

__all__ = [
    "CatalogException",
    "CurriculumNotFound",
    "DuplicateCurriculum",
    "CurriculumStatusConflict",
    "CurriculumImmutable",
    "SubjectNotFound",
    "DuplicateSubject",
    "PrerequisiteCycleDetected",
    "PrerequisiteNotFound",
    "PrerequisiteInUse",
    "AssessmentSchemeInvalid",
]
