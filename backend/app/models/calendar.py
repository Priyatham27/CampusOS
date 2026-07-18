from datetime import datetime
from enum import Enum
from typing import Optional, List
from pymongo import IndexModel
from pydantic import Field, field_validator, model_validator
from beanie import PydanticObjectId

from app.models.base import BaseDocument
from app.models.org_engine.organization import validate_professional_id

class CalendarStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"

class TimelineStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"

class HolidayType(str, Enum):
    PUBLIC = "PUBLIC"
    INSTITUTIONAL = "INSTITUTIONAL"
    RESTRICTED = "RESTRICTED"

class WindowType(str, Enum):
    REGISTRATION = "REGISTRATION"
    EXAMINATION = "EXAMINATION"
    RESULT = "RESULT"
    CERTIFICATE = "CERTIFICATE"
    CUSTOM = "CUSTOM"

class AcademicCalendar(BaseDocument):
    calendar_id: str = Field(..., alias="calendarId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    name: str = Field(..., min_length=2, max_length=150)
    timezone: str = Field(default="UTC")
    is_active: bool = Field(default=False, alias="isActive")
    status: CalendarStatus = Field(default=CalendarStatus.DRAFT)
    weekly_working_days: List[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4], alias="weeklyWorkingDays")

    @field_validator("calendar_id")
    @classmethod
    def validate_cal_id(cls, v: str) -> str:
        return validate_professional_id(v, "CAL")

    class Settings:
        name = "academic_calendars"
        indexes = [
            IndexModel("calendarId", unique=True),
            IndexModel("organizationId"),
            IndexModel([("organizationId", 1), ("isActive", 1)]),
        ]

class AcademicYearTimeline(BaseDocument):
    timeline_id: str = Field(..., alias="timelineId")
    calendar_id: PydanticObjectId = Field(..., alias="calendarId")
    academic_year_id: PydanticObjectId = Field(..., alias="academicYearId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    start_date: datetime = Field(..., alias="startDate")
    end_date: datetime = Field(..., alias="endDate")
    status: TimelineStatus = Field(default=TimelineStatus.DRAFT)

    @field_validator("timeline_id")
    @classmethod
    def validate_timeline_id(cls, v: str) -> str:
        return validate_professional_id(v, "ACYT")

    @model_validator(mode="after")
    def validate_dates(self) -> "AcademicYearTimeline":
        if self.end_date <= self.start_date:
            raise ValueError("endDate must be chronologically after startDate")
        return self

    class Settings:
        name = "academic_year_timelines"
        indexes = [
            IndexModel("timelineId", unique=True),
            IndexModel("calendarId"),
            IndexModel("organizationId"),
            IndexModel([("organizationId", 1), ("calendarId", 1), ("academicYearId", 1)], unique=True),
        ]

class SemesterTimeline(BaseDocument):
    timeline_id: str = Field(..., alias="timelineId")
    academic_year_timeline_id: PydanticObjectId = Field(..., alias="academicYearTimelineId")
    semester_id: PydanticObjectId = Field(..., alias="semesterId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    start_date: datetime = Field(..., alias="startDate")
    end_date: datetime = Field(..., alias="endDate")
    status: TimelineStatus = Field(default=TimelineStatus.DRAFT)

    @field_validator("timeline_id")
    @classmethod
    def validate_timeline_id(cls, v: str) -> str:
        return validate_professional_id(v, "SEMT")

    @model_validator(mode="after")
    def validate_dates(self) -> "SemesterTimeline":
        if self.end_date <= self.start_date:
            raise ValueError("endDate must be chronologically after startDate")
        return self

    class Settings:
        name = "semester_timelines"
        indexes = [
            IndexModel("timelineId", unique=True),
            IndexModel("academicYearTimelineId"),
            IndexModel("organizationId"),
            IndexModel([("organizationId", 1), ("academicYearTimelineId", 1), ("semesterId", 1)], unique=True),
        ]

class Holiday(BaseDocument):
    holiday_id: str = Field(..., alias="holidayId")
    calendar_id: PydanticObjectId = Field(..., alias="calendarId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    name: str = Field(..., min_length=2, max_length=150)
    date: datetime = Field(...)
    type: HolidayType = Field(default=HolidayType.PUBLIC)
    description: Optional[str] = Field(default=None)

    @field_validator("holiday_id")
    @classmethod
    def validate_hol_id(cls, v: str) -> str:
        return validate_professional_id(v, "HOL")

    class Settings:
        name = "holidays"
        indexes = [
            IndexModel("holidayId", unique=True),
            IndexModel("calendarId"),
            IndexModel("organizationId"),
            IndexModel([("calendarId", 1), ("date", 1)], unique=True),
        ]

class WorkingDay(BaseDocument):
    working_day_id: str = Field(..., alias="workingDayId")
    calendar_id: PydanticObjectId = Field(..., alias="calendarId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    date: datetime = Field(...)
    description: Optional[str] = Field(default=None)

    @field_validator("working_day_id")
    @classmethod
    def validate_wkd_id(cls, v: str) -> str:
        return validate_professional_id(v, "WKD")

    class Settings:
        name = "working_days"
        indexes = [
            IndexModel("workingDayId", unique=True),
            IndexModel("calendarId"),
            IndexModel("organizationId"),
            IndexModel([("calendarId", 1), ("date", 1)], unique=True),
        ]

class SchedulingWindow(BaseDocument):
    window_id: str = Field(..., alias="windowId")
    calendar_id: PydanticObjectId = Field(..., alias="calendarId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    semester_timeline_id: Optional[PydanticObjectId] = Field(default=None, alias="semesterTimelineId")
    window_type: WindowType = Field(..., alias="windowType")
    activity_type: str = Field(..., alias="activityType")
    name: str = Field(..., min_length=2, max_length=150)
    start_date: datetime = Field(..., alias="startDate")
    end_date: datetime = Field(..., alias="endDate")
    is_active: bool = Field(default=True, alias="isActive")

    @field_validator("window_id")
    @classmethod
    def validate_win_id(cls, v: str) -> str:
        return validate_professional_id(v, "WIN")

    @model_validator(mode="after")
    def validate_dates(self) -> "SchedulingWindow":
        if self.end_date <= self.start_date:
            raise ValueError("endDate must be chronologically after startDate")
        return self

    class Settings:
        name = "scheduling_windows"
        indexes = [
            IndexModel("windowId", unique=True),
            IndexModel("calendarId"),
            IndexModel("organizationId"),
            IndexModel("semesterTimelineId"),
            IndexModel([("organizationId", 1), ("windowType", 1), ("activityType", 1)]),
        ]

class CalendarEvent(BaseDocument):
    event_id: str = Field(..., alias="eventId")
    calendar_id: PydanticObjectId = Field(..., alias="calendarId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    name: str = Field(..., min_length=2, max_length=150)
    start_date: datetime = Field(..., alias="startDate")
    end_date: datetime = Field(..., alias="endDate")
    description: Optional[str] = Field(default=None)
    category: str = Field(default="ACADEMIC")

    @field_validator("event_id")
    @classmethod
    def validate_cve_id(cls, v: str) -> str:
        return validate_professional_id(v, "CVE")

    @model_validator(mode="after")
    def validate_dates(self) -> "CalendarEvent":
        if self.end_date <= self.start_date:
            raise ValueError("endDate must be chronologically after startDate")
        return self

    class Settings:
        name = "calendar_events"
        indexes = [
            IndexModel("eventId", unique=True),
            IndexModel("calendarId"),
            IndexModel("organizationId"),
        ]

CALENDAR_MODELS = [
    AcademicCalendar,
    AcademicYearTimeline,
    SemesterTimeline,
    Holiday,
    WorkingDay,
    SchedulingWindow,
    CalendarEvent
]

__all__ = [
    "AcademicCalendar",
    "AcademicYearTimeline",
    "SemesterTimeline",
    "Holiday",
    "WorkingDay",
    "SchedulingWindow",
    "CalendarEvent",
    "CalendarStatus",
    "TimelineStatus",
    "HolidayType",
    "WindowType",
    "CALENDAR_MODELS"
]

