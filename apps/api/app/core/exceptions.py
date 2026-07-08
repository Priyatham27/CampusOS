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

class CapabilityNotFound(OrganizationException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Capability not found."

class CapabilityAlreadyExists(OrganizationException):
    status_code: int = status.HTTP_409_CONFLICT
    detail: str = "Capability already exists."

class DependencyMissing(OrganizationException):
    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "Required capability dependency is missing or disabled."

class CircularDependency(OrganizationException):
    status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail: str = "Circular capability dependencies detected."

class LicenseViolation(OrganizationException):
    status_code: int = status.HTTP_403_FORBIDDEN
    detail: str = "Organization subscription license tier does not cover this capability."

class CompatibilityViolation(OrganizationException):
    status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail: str = "Compatibility violation with existing enabled capabilities."

class CoreModuleProtected(OrganizationException):
    status_code: int = status.HTTP_403_FORBIDDEN
    detail: str = "Core system capabilities cannot be disabled or deleted."

class ConfigurationNotFound(OrganizationException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Configuration key not found."

class DuplicateConfiguration(OrganizationException):
    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "Configuration key already exists in this scope and environment."

class InvalidScope(OrganizationException):
    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "Invalid configuration scope provided."

class InvalidEnvironment(OrganizationException):
    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "Invalid runtime environment provided."

class RolloutConflict(OrganizationException):
    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "Invalid rollout configuration constraints."

class FeatureNotFound(OrganizationException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Feature flag not found."



