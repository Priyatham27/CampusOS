"""
Academic Domain Exception Hierarchy
====================================
All exceptions raised by the Academic bounded context are defined here.
Handlers for AcademicException are registered in main.py.

Exception hierarchy:
    AcademicException (base)
    ├── AcademicYearNotFound
    ├── DuplicateAcademicYear
    ├── AcademicYearConflict
    ├── DepartmentNotFound
    ├── DuplicateDepartment
    ├── ProgramNotFound
    ├── DuplicateProgram
    ├── BranchNotFound
    ├── DuplicateBranch
    ├── SemesterNotFound
    ├── DuplicateSemester
    ├── SemesterSequenceViolation
    ├── SectionNotFound
    ├── DuplicateSection
    ├── CourseNotFound
    ├── DuplicateCourse
    └── AcademicHierarchyViolation
"""
from fastapi import status


class AcademicException(Exception):
    """Base class for all Academic domain exceptions."""
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "An unexpected error occurred in the Academic Platform."

    def __init__(self, detail: str = None):
        if detail:
            self.detail = detail
        super().__init__(self.detail)


# ── Academic Year ──────────────────────────────────────────────────────────────

class AcademicYearNotFound(AcademicException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Academic year not found."


class DuplicateAcademicYear(AcademicException):
    status_code: int = status.HTTP_409_CONFLICT
    detail: str = "An academic year with this name already exists in the organization."


class AcademicYearConflict(AcademicException):
    """Raised when setting current=True while another active year already exists."""
    status_code: int = status.HTTP_409_CONFLICT
    detail: str = "Only one academic year can be marked as current at a time."


# ── Department ─────────────────────────────────────────────────────────────────

class DepartmentNotFound(AcademicException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Department not found."


class DuplicateDepartment(AcademicException):
    status_code: int = status.HTTP_409_CONFLICT
    detail: str = "A department with this code already exists in the organization."


# ── Program ───────────────────────────────────────────────────────────────────

class ProgramNotFound(AcademicException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Program not found."


class DuplicateProgram(AcademicException):
    status_code: int = status.HTTP_409_CONFLICT
    detail: str = "A program with this name already exists in the department."


# ── Branch ────────────────────────────────────────────────────────────────────

class BranchNotFound(AcademicException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Branch not found."


class DuplicateBranch(AcademicException):
    status_code: int = status.HTTP_409_CONFLICT
    detail: str = "A branch with this code already exists in the department."


# ── Semester ──────────────────────────────────────────────────────────────────

class SemesterNotFound(AcademicException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Semester not found."


class DuplicateSemester(AcademicException):
    status_code: int = status.HTTP_409_CONFLICT
    detail: str = "A semester with this number already exists in the organization."


class SemesterSequenceViolation(AcademicException):
    """Raised when semester numbers would become non-sequential."""
    status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail: str = "Semester numbers must be sequential. Cannot skip or reorder semester numbers."


# ── Section ───────────────────────────────────────────────────────────────────

class SectionNotFound(AcademicException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Section not found."


class DuplicateSection(AcademicException):
    status_code: int = status.HTTP_409_CONFLICT
    detail: str = "A section with this name already exists for the branch and semester."


# ── Course ────────────────────────────────────────────────────────────────────

class CourseNotFound(AcademicException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Course not found."


class DuplicateCourse(AcademicException):
    status_code: int = status.HTTP_409_CONFLICT
    detail: str = "A course with this code already exists in the organization."


# ── Generic Hierarchy ─────────────────────────────────────────────────────────

class AcademicHierarchyViolation(AcademicException):
    """Raised when a cross-entity reference constraint is violated."""
    status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail: str = "Academic hierarchy constraint violation."
