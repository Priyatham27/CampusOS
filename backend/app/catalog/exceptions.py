from fastapi import HTTPException


class CatalogException(HTTPException):
    """Base exception for all Catalog Engine errors."""
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)


class CurriculumNotFound(CatalogException):
    def __init__(self, curriculum_id: str = ""):
        super().__init__(
            status_code=404,
            detail=f"Curriculum '{curriculum_id}' was not found in this organization."
        )


class DuplicateCurriculum(CatalogException):
    def __init__(self, version: int = 0, program_id: str = ""):
        super().__init__(
            status_code=409,
            detail=f"Curriculum version {version} already exists for program '{program_id}'."
        )


class CurriculumStatusConflict(CatalogException):
    def __init__(self, action: str = "", current_status: str = ""):
        super().__init__(
            status_code=409,
            detail=(
                f"Cannot perform '{action}' on a curriculum with status '{current_status}'. "
                "Check the lifecycle rules: DRAFT→ACTIVE→ARCHIVED."
            )
        )


class CurriculumImmutable(CatalogException):
    def __init__(self):
        super().__init__(
            status_code=422,
            detail="Only curricula in DRAFT status can be modified or deleted. "
                   "Clone this curriculum to create an editable version."
        )


class SubjectNotFound(CatalogException):
    def __init__(self, subject_id: str = ""):
        super().__init__(
            status_code=404,
            detail=f"Subject '{subject_id}' was not found in this curriculum."
        )


class DuplicateSubject(CatalogException):
    def __init__(self, subject_code: str = ""):
        super().__init__(
            status_code=409,
            detail=f"A subject with code '{subject_code}' already exists in this curriculum."
        )


class PrerequisiteCycleDetected(CatalogException):
    def __init__(self, cycle_path: str = ""):
        detail = "Prerequisite dependency cycle detected — this would create a circular requirement."
        if cycle_path:
            detail += f" Cycle path: {cycle_path}"
        super().__init__(status_code=422, detail=detail)


class PrerequisiteNotFound(CatalogException):
    def __init__(self, subject_id: str = ""):
        super().__init__(
            status_code=422,
            detail=f"Prerequisite subject '{subject_id}' does not exist in this curriculum."
        )


class PrerequisiteInUse(CatalogException):
    def __init__(self, subject_id: str = "", dependents: str = ""):
        super().__init__(
            status_code=422,
            detail=f"Cannot delete subject '{subject_id}'. It is a prerequisite for: {dependents}."
        )


class AssessmentSchemeInvalid(CatalogException):
    def __init__(self, total: float = 0.0):
        super().__init__(
            status_code=422,
            detail=f"Assessment component weights must sum to exactly 100%. Current total: {total:.2f}%."
        )
