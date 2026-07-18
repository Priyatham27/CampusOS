from fastapi import status

class StudentException(Exception):
    """Base exception for the Student Bounded Context."""
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "An unexpected error occurred in the Student Platform."

    def __init__(self, detail: str = None):
        if detail:
            self.detail = detail
        super().__init__(self.detail)

class StudentNotFound(StudentException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Student not found."

class DuplicateRollNumber(StudentException):
    status_code: int = status.HTTP_409_CONFLICT
    detail: str = "A student with this roll number already exists in this organization."

class StudentArchivedReadOnly(StudentException):
    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "This student record is archived and remains read-only."

class GuardianLimitExceeded(StudentException):
    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "Maximum number of guardians reached."

class GuardianNotFound(StudentException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Guardian not found."

class DocumentNotFound(StudentException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Document not found."

class AchievementNotFound(StudentException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Achievement not found."

class SkillNotFound(StudentException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Skill not found."
