from fastapi import status

class CredentialException(Exception):
    """Base exception for all Credential Engine domain exceptions."""
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "An unexpected error occurred in the Credential Engine."

    def __init__(self, detail: str = None):
        if detail:
            self.detail = detail
        super().__init__(self.detail)

class CredentialNotFound(CredentialException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Credential not found."

class CredentialAlreadyExists(CredentialException):
    status_code: int = status.HTTP_409_CONFLICT
    detail: str = "Credential already exists for this user."

class InvalidPassword(CredentialException):
    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "Incorrect current password."

class PasswordPolicyViolation(CredentialException):
    status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail: str = "Password does not meet complexity requirements."

class PasswordReuseProhibited(CredentialException):
    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "New password cannot be the same as any of the last 5 passwords used."

class CredentialLocked(CredentialException):
    status_code: int = status.HTTP_403_FORBIDDEN
    detail: str = "Account is temporarily locked due to too many failed login attempts."

class EmailNotVerified(CredentialException):
    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "Email must be verified before credential activation."
