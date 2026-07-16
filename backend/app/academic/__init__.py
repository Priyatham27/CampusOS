"""
Academic Bounded Context — CampusOS Platform
============================================
This module is the canonical Academic domain for CampusOS.
All academic data (years, departments, programs, branches,
semesters, sections, courses) is owned and managed here.

External bounded contexts (Student, Faculty, Events, etc.)
MUST consume academic data through this module's public interfaces
and MUST NOT access the underlying MongoDB collections directly.

Public API surface:
    - AcademicService (aggregated facade)
    - Individual entity services (AcademicYearService, DepartmentService, etc.)
    - AcademicException hierarchy
    - Pydantic schemas
"""

from app.academic.exceptions import (
    AcademicException,
    AcademicYearNotFound,
    DuplicateAcademicYear,
    AcademicYearConflict,
    DepartmentNotFound,
    DuplicateDepartment,
    ProgramNotFound,
    DuplicateProgram,
    BranchNotFound,
    DuplicateBranch,
    SemesterNotFound,
    DuplicateSemester,
    SemesterSequenceViolation,
    SectionNotFound,
    DuplicateSection,
    CourseNotFound,
    DuplicateCourse,
    AcademicHierarchyViolation,
)

__all__ = [
    "AcademicException",
    "AcademicYearNotFound",
    "DuplicateAcademicYear",
    "AcademicYearConflict",
    "DepartmentNotFound",
    "DuplicateDepartment",
    "ProgramNotFound",
    "DuplicateProgram",
    "BranchNotFound",
    "DuplicateBranch",
    "SemesterNotFound",
    "DuplicateSemester",
    "SemesterSequenceViolation",
    "SectionNotFound",
    "DuplicateSection",
    "CourseNotFound",
    "DuplicateCourse",
    "AcademicHierarchyViolation",
]
