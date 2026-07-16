from fastapi import status

class AuthorizationException(Exception):
    """Base authorization exception."""
    status_code: int = status.HTTP_403_FORBIDDEN
    detail: str = "Access denied."

    def __init__(self, detail: Optional[str] = None):
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)

from typing import Optional

class RoleNotFound(AuthorizationException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Role was not found."

class PermissionNotFound(AuthorizationException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Permission was not found."

class AuthorizationDenied(AuthorizationException):
    status_code: int = status.HTTP_403_FORBIDDEN
    detail: str = "Authorization denied."

class PolicyViolation(AuthorizationException):
    status_code: int = status.HTTP_403_FORBIDDEN
    detail: str = "Policy violation: request blocked."

class ImmutableRole(AuthorizationException):
    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "System roles cannot be modified or deleted."

class InvalidPermission(AuthorizationException):
    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "Permission formatting is invalid or incompatible."
