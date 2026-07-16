from fastapi import status

class AuthenticationException(Exception):
    """Base exception for all Authentication Engine domain exceptions."""
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "An unexpected error occurred in the Authentication Engine."

    def __init__(self, detail: str = None):
        if detail:
            self.detail = detail
        super().__init__(self.detail)

class AuthenticationFailed(AuthenticationException):
    status_code: int = status.HTTP_401_UNAUTHORIZED
    detail: str = "Incorrect email/username or password."

class AccountLocked(AuthenticationException):
    status_code: int = status.HTTP_403_FORBIDDEN
    detail: str = "Account is temporarily locked due to too many failed login attempts."

class AccountDisabled(AuthenticationException):
    status_code: int = status.HTTP_403_FORBIDDEN
    detail: str = "Account has been suspended or deactivated."

class OrganizationNotFound(AuthenticationException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Organization not found."

class CredentialNotFound(AuthenticationException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Credential not found for this user."

class EmailNotVerified(AuthenticationException):
    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "Email must be verified before logging in."

class InvalidToken(AuthenticationException):
    status_code: int = status.HTTP_401_UNAUTHORIZED
    detail: str = "Invalid or expired authentication token."
