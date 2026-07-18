from pydantic import BaseModel, Field, ConfigDict, BeforeValidator
from datetime import datetime
from typing import Optional, List, Any
from typing_extensions import Annotated
from app.models.calendar import CalendarStatus, TimelineStatus, HolidayType, WindowType

# Annotated validator to stringify MongoDB ObjectIDs before validation runs
PyObjectIdStr = Annotated[str, BeforeValidator(lambda v: str(v) if v is not None else None)]

schema_config = ConfigDict(
    populate_by_name=True,
    from_attributes=True,
    use_enum_values=True
)

# ==========================================
# ACADEMIC CALENDARS
# ==========================================

class CalendarCreateSchema(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    timezone: str = Field(default="UTC")
    weeklyWorkingDays: List[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4], alias="weeklyWorkingDays")
    model_config = schema_config

class CalendarUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    timezone: Optional[str] = Field(None)
    weeklyWorkingDays: Optional[List[int]] = Field(None, alias="weeklyWorkingDays")
    model_config = schema_config

class CalendarResponseSchema(BaseModel):
    id: PyObjectIdStr = Field(..., alias="id")
    calendar_id: str = Field(..., alias="calendarId")
    organization_id: PyObjectIdStr = Field(..., alias="organizationId")
    name: str
    timezone: str
    is_active: bool = Field(..., alias="isActive")
    status: CalendarStatus
    weekly_working_days: List[int] = Field(..., alias="weeklyWorkingDays")
    model_config = schema_config

# ==========================================
# TIMELINES (ACADEMIC YEAR)
# ==========================================

class AcademicYearTimelineCreateSchema(BaseModel):
    calendarId: str = Field(..., alias="calendarId")
    academicYearId: str = Field(..., alias="academicYearId")
    startDate: datetime = Field(..., alias="startDate")
    endDate: datetime = Field(..., alias="endDate")
    status: TimelineStatus = Field(default=TimelineStatus.DRAFT)
    model_config = schema_config

class AcademicYearTimelineUpdateSchema(BaseModel):
    startDate: Optional[datetime] = Field(None, alias="startDate")
    endDate: Optional[datetime] = Field(None, alias="endDate")
    status: Optional[TimelineStatus] = Field(None)
    model_config = schema_config

class AcademicYearTimelineResponseSchema(BaseModel):
    id: PyObjectIdStr = Field(..., alias="id")
    timeline_id: str = Field(..., alias="timelineId")
    calendar_id: PyObjectIdStr = Field(..., alias="calendarId")
    academic_year_id: PyObjectIdStr = Field(..., alias="academicYearId")
    organization_id: PyObjectIdStr = Field(..., alias="organizationId")
    start_date: datetime = Field(..., alias="startDate")
    end_date: datetime = Field(..., alias="endDate")
    status: TimelineStatus
    model_config = schema_config

# ==========================================
# TIMELINES (SEMESTER)
# ==========================================

class SemesterTimelineCreateSchema(BaseModel):
    academicYearTimelineId: str = Field(..., alias="academicYearTimelineId")
    semesterId: str = Field(..., alias="semesterId")
    startDate: datetime = Field(..., alias="startDate")
    endDate: datetime = Field(..., alias="endDate")
    status: TimelineStatus = Field(default=TimelineStatus.DRAFT)
    model_config = schema_config

class SemesterTimelineUpdateSchema(BaseModel):
    startDate: Optional[datetime] = Field(None, alias="startDate")
    endDate: Optional[datetime] = Field(None, alias="endDate")
    status: Optional[TimelineStatus] = Field(None)
    model_config = schema_config

class SemesterTimelineResponseSchema(BaseModel):
    id: PyObjectIdStr = Field(..., alias="id")
    timeline_id: str = Field(..., alias="timelineId")
    academic_year_timeline_id: PyObjectIdStr = Field(..., alias="academicYearTimelineId")
    semester_id: PyObjectIdStr = Field(..., alias="semesterId")
    organization_id: PyObjectIdStr = Field(..., alias="organizationId")
    start_date: datetime = Field(..., alias="startDate")
    end_date: datetime = Field(..., alias="endDate")
    status: TimelineStatus
    model_config = schema_config

# ==========================================
# HOLIDAYS
# ==========================================

class HolidayCreateSchema(BaseModel):
    calendarId: str = Field(..., alias="calendarId")
    name: str = Field(..., min_length=2, max_length=150)
    date: datetime = Field(...)
    type: HolidayType = Field(default=HolidayType.PUBLIC)
    description: Optional[str] = Field(default=None)
    model_config = schema_config

class HolidayUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    date: Optional[datetime] = Field(None)
    type: Optional[HolidayType] = Field(None)
    description: Optional[str] = Field(default=None)
    model_config = schema_config

class HolidayResponseSchema(BaseModel):
    id: PyObjectIdStr = Field(..., alias="id")
    holiday_id: str = Field(..., alias="holidayId")
    calendar_id: PyObjectIdStr = Field(..., alias="calendarId")
    organization_id: PyObjectIdStr = Field(..., alias="organizationId")
    name: str
    date: datetime
    type: HolidayType
    description: Optional[str] = None
    model_config = schema_config

# ==========================================
# WORKING DAYS
# ==========================================

class WorkingDayCreateSchema(BaseModel):
    calendarId: str = Field(..., alias="calendarId")
    date: datetime = Field(...)
    description: Optional[str] = Field(default=None)
    model_config = schema_config

class WorkingDayUpdateSchema(BaseModel):
    date: Optional[datetime] = Field(None)
    description: Optional[str] = Field(default=None)
    model_config = schema_config

class WorkingDayResponseSchema(BaseModel):
    id: PyObjectIdStr = Field(..., alias="id")
    working_day_id: str = Field(..., alias="workingDayId")
    calendar_id: PyObjectIdStr = Field(..., alias="calendarId")
    organization_id: PyObjectIdStr = Field(..., alias="organizationId")
    date: datetime
    description: Optional[str] = None
    model_config = schema_config

# ==========================================
# SCHEDULING WINDOWS
# ==========================================

class SchedulingWindowCreateSchema(BaseModel):
    calendarId: str = Field(..., alias="calendarId")
    semesterTimelineId: Optional[str] = Field(default=None, alias="semesterTimelineId")
    windowType: WindowType = Field(..., alias="windowType")
    activityType: str = Field(..., alias="activityType")
    name: str = Field(..., min_length=2, max_length=150)
    startDate: datetime = Field(..., alias="startDate")
    endDate: datetime = Field(..., alias="endDate")
    isActive: bool = Field(default=True, alias="isActive")
    model_config = schema_config

class SchedulingWindowUpdateSchema(BaseModel):
    semesterTimelineId: Optional[str] = Field(default=None, alias="semesterTimelineId")
    windowType: Optional[WindowType] = Field(None, alias="windowType")
    activityType: Optional[str] = Field(None, alias="activityType")
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    startDate: Optional[datetime] = Field(None, alias="startDate")
    endDate: Optional[datetime] = Field(None, alias="endDate")
    isActive: Optional[bool] = Field(None, alias="isActive")
    model_config = schema_config

class SchedulingWindowResponseSchema(BaseModel):
    id: PyObjectIdStr = Field(..., alias="id")
    window_id: str = Field(..., alias="windowId")
    calendar_id: PyObjectIdStr = Field(..., alias="calendarId")
    organization_id: PyObjectIdStr = Field(..., alias="organizationId")
    semester_timeline_id: Optional[PyObjectIdStr] = Field(default=None, alias="semesterTimelineId")
    window_type: WindowType = Field(..., alias="windowType")
    activity_type: str = Field(..., alias="activityType")
    name: str
    start_date: datetime = Field(..., alias="startDate")
    end_date: datetime = Field(..., alias="endDate")
    is_active: bool = Field(..., alias="isActive")
    model_config = schema_config

# ==========================================
# CALENDAR EVENTS
# ==========================================

class CalendarEventCreateSchema(BaseModel):
    calendarId: str = Field(..., alias="calendarId")
    name: str = Field(..., min_length=2, max_length=150)
    startDate: datetime = Field(..., alias="startDate")
    endDate: datetime = Field(..., alias="endDate")
    description: Optional[str] = Field(default=None)
    category: str = Field(default="ACADEMIC")
    model_config = schema_config

class CalendarEventUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    startDate: Optional[datetime] = Field(None, alias="startDate")
    endDate: Optional[datetime] = Field(None, alias="endDate")
    description: Optional[str] = Field(default=None)
    category: Optional[str] = Field(None)
    model_config = schema_config

class CalendarEventResponseSchema(BaseModel):
    id: PyObjectIdStr = Field(..., alias="id")
    event_id: str = Field(..., alias="eventId")
    calendar_id: PyObjectIdStr = Field(..., alias="calendarId")
    organization_id: PyObjectIdStr = Field(..., alias="organizationId")
    name: str
    start_date: datetime = Field(..., alias="startDate")
    end_date: datetime = Field(..., alias="endDate")
    description: Optional[str] = None
    category: str
    model_config = schema_config

# ==========================================
# CONSOLIDATED TIMELINE RESPONSE
# ==========================================

class UnifiedTimelineResponseSchema(BaseModel):
    activeCalendar: Optional[CalendarResponseSchema] = Field(None, alias="activeCalendar")
    academicYearTimelines: List[AcademicYearTimelineResponseSchema] = Field(default_factory=list, alias="academicYearTimelines")
    semesterTimelines: List[SemesterTimelineResponseSchema] = Field(default_factory=list, alias="semesterTimelines")
    holidays: List[HolidayResponseSchema] = Field(default_factory=list, alias="holidays")
    workingDays: List[WorkingDayResponseSchema] = Field(default_factory=list, alias="workingDays")
    schedulingWindows: List[SchedulingWindowResponseSchema] = Field(default_factory=list, alias="schedulingWindows")
    calendarEvents: List[CalendarEventResponseSchema] = Field(default_factory=list, alias="calendarEvents")
    model_config = schema_config
