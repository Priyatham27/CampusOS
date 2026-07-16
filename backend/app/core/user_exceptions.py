from fastapi import status

class UserException(Exception):
    """Base class for all User Management domain exceptions."""
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "An unexpected error occurred in the User Management Platform."

    def __init__(self, detail: str = None):
        if detail:
            self.detail = detail
        super().__init__(self.detail)

class UserNotFound(UserException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "User not found."

class ProfileNotFound(UserException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "User profile not found."

class DuplicateEmail(UserException):
    status_code: int = status.HTTP_409_CONFLICT
    detail: str = "Email address already registered."

class DuplicateUsername(UserException):
    status_code: int = status.HTTP_409_CONFLICT
    detail: str = "Username already exists within the organization."

class InvalidOrganization(UserException):
    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "Referenced organization is invalid, inactive, or does not exist."

class BulkImportFailed(UserException):
    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "Bulk import operation failed."

class AvatarUploadFailed(UserException):
    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "Avatar image upload processing failed."
