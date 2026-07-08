from fastapi import status

class OrganizationException(Exception):
    """Base class for all Organization Engine domain exceptions."""
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "An unexpected error occurred in the Organization Engine."

    def __init__(self, detail: str = None):
        if detail:
            self.detail = detail
        super().__init__(self.detail)

class OrganizationNotFound(OrganizationException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Organization not found."

class OrganizationAlreadyExists(OrganizationException):
    status_code: int = status.HTTP_409_CONFLICT
    detail: str = "Organization already exists."

class SlugAlreadyExists(OrganizationException):
    status_code: int = status.HTTP_409_CONFLICT
    detail: str = "Organization slug is already in use."

class EmailDomainAlreadyExists(OrganizationException):
    status_code: int = status.HTTP_409_CONFLICT
    detail: str = "Institution email domain is already registered."

class ValidationException(OrganizationException):
    status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail: str = "Invalid request payload parameters provided."

class BrandingNotFound(OrganizationException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Branding configuration not found for organization."

class InvalidColor(OrganizationException):
    status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail: str = "Invalid HEX color format."

class InvalidImage(OrganizationException):
    status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail: str = "Invalid image asset format or constraint violation."

class InvalidTheme(OrganizationException):
    status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail: str = "Invalid theme configuration selection."

class UploadFailed(OrganizationException):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "Image upload processing failed."

class DepartmentNotFound(OrganizationException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Department not found."

class ProgramNotFound(OrganizationException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Program not found."

class BranchNotFound(OrganizationException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Branch not found."

class SemesterNotFound(OrganizationException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Semester not found."

class SectionNotFound(OrganizationException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Section not found."

class CourseNotFound(OrganizationException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Course not found."

class DuplicateDepartment(OrganizationException):
    status_code: int = status.HTTP_409_CONFLICT
    detail: str = "Department code is already registered in this organization."

class DuplicateCourse(OrganizationException):
    status_code: int = status.HTTP_409_CONFLICT
    detail: str = "Course code is already registered in this organization."

class DuplicateSemester(OrganizationException):
    status_code: int = status.HTTP_409_CONFLICT
    detail: str = "Semester number is already registered in this organization."

class HierarchyViolation(OrganizationException):
    status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail: str = "Hierarchy mapping constraint violation."


