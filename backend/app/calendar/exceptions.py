from fastapi import status
from app.academic.exceptions import AcademicException

class CalendarException(AcademicException):
    """Base exception for all Calendar and Scheduling domain errors."""
    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "A scheduling or calendar error occurred."

class CalendarNotFound(CalendarException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Academic calendar not found."

class TimelineConflict(CalendarException):
    status_code: int = status.HTTP_409_CONFLICT
    detail: str = "Timeline boundaries overlap or conflict with an existing configuration."

class WindowOverlapException(CalendarException):
    status_code: int = status.HTTP_409_CONFLICT
    detail: str = "A registration or scheduling window overlaps with another active window of the same type."
