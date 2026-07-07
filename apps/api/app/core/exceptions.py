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
