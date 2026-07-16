from fastapi import status

class SessionException(Exception):
    """Base exception for all Session & Device Engine domain exceptions."""
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "An unexpected error occurred in the Session Engine."

    def __init__(self, detail: str = None):
        if detail:
            self.detail = detail
        super().__init__(self.detail)

class SessionNotFound(SessionException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Session not found."

class SessionExpired(SessionException):
    status_code: int = status.HTTP_401_UNAUTHORIZED
    detail: str = "Session has expired."

class RefreshTokenInvalid(SessionException):
    status_code: int = status.HTTP_401_UNAUTHORIZED
    detail: str = "Invalid refresh token."

class RefreshTokenExpired(SessionException):
    status_code: int = status.HTTP_401_UNAUTHORIZED
    detail: str = "Refresh token has expired."

class DeviceNotFound(SessionException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Device registration not found."

class SessionRevoked(SessionException):
    status_code: int = status.HTTP_401_UNAUTHORIZED
    detail: str = "Session has been revoked."

class TooManySessions(SessionException):
    status_code: int = status.HTTP_403_FORBIDDEN
    detail: str = "Concurrent session limit exceeded."
