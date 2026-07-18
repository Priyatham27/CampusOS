from datetime import datetime
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, Query, Body, Request, status, Response
from fastapi.responses import StreamingResponse
from beanie import PydanticObjectId
import io

from app.schemas.schemas import APIResponse
from app.schemas.calendar_schemas import (
    CalendarCreateSchema, CalendarUpdateSchema, CalendarResponseSchema,
    AcademicYearTimelineCreateSchema, AcademicYearTimelineUpdateSchema, AcademicYearTimelineResponseSchema,
    SemesterTimelineCreateSchema, SemesterTimelineUpdateSchema, SemesterTimelineResponseSchema,
    HolidayCreateSchema, HolidayUpdateSchema, HolidayResponseSchema,
    WorkingDayCreateSchema, WorkingDayUpdateSchema, WorkingDayResponseSchema,
    SchedulingWindowCreateSchema, SchedulingWindowUpdateSchema, SchedulingWindowResponseSchema,
    CalendarEventCreateSchema, CalendarEventUpdateSchema, CalendarEventResponseSchema,
    UnifiedTimelineResponseSchema
)
from app.calendar.service import (
    CalendarService, TimelineService, HolidayService, WindowService
)
from app.models.calendar import WindowType
from app.core.identity_context import check_permission, get_current_identity
from app.core.database import get_db

router = APIRouter()

def get_calendar_service() -> CalendarService:
    return CalendarService()

def get_timeline_service() -> TimelineService:
    return TimelineService()

def get_holiday_service() -> HolidayService:
    return HolidayService()

def get_window_service() -> WindowService:
    return WindowService()


async def _get_org_oid(org_id_str: str) -> PydanticObjectId:
    """Helper to resolve organizationId string to its PydanticObjectId."""
    db = get_db()
    org = await db["organizations"].find_one({"organizationId": org_id_str, "isDeleted": {"$ne": True}})
    if not org:
        from app.core.exceptions import OrganizationNotFound
        raise OrganizationNotFound(f"Organization '{org_id_str}' not found.")
    return org["_id"]


async def _audit(org_id: Any, action: str, details: dict) -> None:
    """Write an audit log entry to MongoDB."""
    try:
        db = get_db()
        await db["audit_logs"].insert_one({
            "organizationId": org_id,
            "action": action,
            "timestamp": datetime.utcnow(),
            "performedBy": "system",
            "module": "calendar",
            "details": details,
        })
    except Exception:
        pass


# ============================================================================
# ACADEMIC CALENDARS
# ============================================================================

@router.post(
    "/organizations/{organizationId}/calendars",
    response_model=APIResponse[CalendarResponseSchema],
    summary="Create Academic Calendar",
    tags=["Academic Calendar"],
)
async def create_calendar(
    organizationId: str,
    payload: CalendarCreateSchema,
    service: CalendarService = Depends(get_calendar_service),
    _: Any = Depends(check_permission("academic:write")),
):
    res = await service.create_calendar(organizationId, payload.model_dump(by_alias=True))
    await _audit(res.organization_id, "calendar.created", {"id": res.calendar_id, "name": res.name})
    return APIResponse(success=True, message="Academic Calendar created successfully.", data=res)


@router.get(
    "/organizations/{organizationId}/calendars",
    response_model=APIResponse[List[CalendarResponseSchema]],
    summary="List Academic Calendars",
    tags=["Academic Calendar"],
)
async def list_calendars(
    organizationId: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    sortBy: str = Query("createdAt"),
    sortOrder: str = Query("asc"),
    status: Optional[str] = Query(None),
    isActive: Optional[bool] = Query(None),
    service: CalendarService = Depends(get_calendar_service),
    _: Any = Depends(get_current_identity),
):
    filters = {}
    if status:
        filters["status"] = status
    if isActive is not None:
        filters["isActive"] = isActive
    items, total = await service.list_calendars(organizationId, skip, limit, sortBy, sortOrder, filters)
    return APIResponse(success=True, data=items, meta={"pagination": {"skip": skip, "limit": limit, "total": total}})


@router.get(
    "/organizations/{organizationId}/calendars/{id}",
    response_model=APIResponse[CalendarResponseSchema],
    summary="Get Academic Calendar by ID",
    tags=["Academic Calendar"],
)
async def get_calendar(
    organizationId: str,
    id: str,
    service: CalendarService = Depends(get_calendar_service),
    _: Any = Depends(get_current_identity),
):
    res = await service.get_calendar(organizationId, id)
    return APIResponse(success=True, data=res)


@router.patch(
    "/organizations/{organizationId}/calendars/{id}",
    response_model=APIResponse[CalendarResponseSchema],
    summary="Update Academic Calendar",
    tags=["Academic Calendar"],
)
async def update_calendar(
    organizationId: str,
    id: str,
    payload: CalendarUpdateSchema,
    service: CalendarService = Depends(get_calendar_service),
    _: Any = Depends(check_permission("academic:write")),
):
    res = await service.update_calendar(organizationId, id, payload.model_dump(exclude_unset=True, by_alias=True))
    await _audit(res.organization_id, "calendar.updated", {"id": id})
    return APIResponse(success=True, message="Academic Calendar updated successfully.", data=res)


@router.delete(
    "/organizations/{organizationId}/calendars/{id}",
    response_model=APIResponse[bool],
    summary="Delete Academic Calendar",
    tags=["Academic Calendar"],
)
async def delete_calendar(
    organizationId: str,
    id: str,
    service: CalendarService = Depends(get_calendar_service),
    _: Any = Depends(check_permission("academic:delete")),
):
    res = await service.get_calendar(organizationId, id)
    await service.delete_calendar(organizationId, id)
    await _audit(res.organization_id, "calendar.deleted", {"id": id})
    return APIResponse(success=True, message="Academic Calendar soft deleted.", data=True)


@router.post(
    "/organizations/{organizationId}/calendars/{id}/activate",
    response_model=APIResponse[CalendarResponseSchema],
    summary="Activate Academic Calendar",
    tags=["Academic Calendar"],
)
async def activate_calendar(
    organizationId: str,
    id: str,
    service: CalendarService = Depends(get_calendar_service),
    _: Any = Depends(check_permission("academic:write")),
):
    res = await service.activate_calendar(organizationId, id)
    await _audit(res.organization_id, "calendar.activated", {"id": id})
    return APIResponse(success=True, message="Academic Calendar activated successfully.", data=res)


# ============================================================================
# ACADEMIC YEAR TIMELINES
# ============================================================================

@router.post(
    "/organizations/{organizationId}/academic-year-timelines",
    response_model=APIResponse[AcademicYearTimelineResponseSchema],
    summary="Create Academic Year Timeline",
    tags=["Academic Calendar Timelines"],
)
async def create_academic_year_timeline(
    organizationId: str,
    payload: AcademicYearTimelineCreateSchema,
    service: TimelineService = Depends(get_timeline_service),
    _: Any = Depends(check_permission("academic:write")),
):
    res = await service.create_academic_year_timeline(organizationId, payload.model_dump(by_alias=True))
    await _audit(res.organization_id, "timeline.year_created", {"id": res.timeline_id, "yearId": str(res.academic_year_id)})
    return APIResponse(success=True, message="Academic Year Timeline created successfully.", data=res)


@router.get(
    "/organizations/{organizationId}/academic-year-timelines",
    response_model=APIResponse[List[AcademicYearTimelineResponseSchema]],
    summary="List Academic Year Timelines",
    tags=["Academic Calendar Timelines"],
)
async def list_academic_year_timelines(
    organizationId: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    sortBy: str = Query("startDate"),
    sortOrder: str = Query("asc"),
    calendarId: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    service: TimelineService = Depends(get_timeline_service),
    _: Any = Depends(get_current_identity),
):
    org_oid = await _get_org_oid(organizationId)
    filters = {}
    if calendarId:
        filters["calendarId"] = calendarId
    if status:
        filters["status"] = status
    items = await service.acyt_repo.list(org_oid, skip, limit, sortBy, sortOrder, filters)
    total = await service.acyt_repo.count(org_oid, filters)
    return APIResponse(success=True, data=items, meta={"pagination": {"skip": skip, "limit": limit, "total": total}})


@router.get(
    "/organizations/{organizationId}/academic-year-timelines/{id}",
    response_model=APIResponse[AcademicYearTimelineResponseSchema],
    summary="Get Academic Year Timeline by ID",
    tags=["Academic Calendar Timelines"],
)
async def get_academic_year_timeline(
    organizationId: str,
    id: str,
    service: TimelineService = Depends(get_timeline_service),
    _: Any = Depends(get_current_identity),
):
    org_oid = await _get_org_oid(organizationId)
    res = await service.acyt_repo.find_by_id(id, org_oid)
    return APIResponse(success=True, data=res)


@router.patch(
    "/organizations/{organizationId}/academic-year-timelines/{id}",
    response_model=APIResponse[AcademicYearTimelineResponseSchema],
    summary="Update Academic Year Timeline",
    tags=["Academic Calendar Timelines"],
)
async def update_academic_year_timeline(
    organizationId: str,
    id: str,
    payload: AcademicYearTimelineUpdateSchema,
    service: TimelineService = Depends(get_timeline_service),
    _: Any = Depends(check_permission("academic:write")),
):
    res = await service.update_academic_year_timeline(organizationId, id, payload.model_dump(exclude_unset=True, by_alias=True))
    await _audit(res.organization_id, "timeline.year_updated", {"id": id})
    return APIResponse(success=True, message="Academic Year Timeline updated successfully.", data=res)


@router.delete(
    "/organizations/{organizationId}/academic-year-timelines/{id}",
    response_model=APIResponse[bool],
    summary="Delete Academic Year Timeline",
    tags=["Academic Calendar Timelines"],
)
async def delete_academic_year_timeline(
    organizationId: str,
    id: str,
    service: TimelineService = Depends(get_timeline_service),
    _: Any = Depends(check_permission("academic:delete")),
):
    org_oid = await _get_org_oid(organizationId)
    res = await service.acyt_repo.find_by_id(id, org_oid)
    await service.delete_academic_year_timeline(organizationId, id)
    await _audit(res.organization_id, "timeline.year_deleted", {"id": id})
    return APIResponse(success=True, message="Academic Year Timeline soft deleted.", data=True)


# ============================================================================
# SEMESTER TIMELINES
# ============================================================================

@router.post(
    "/organizations/{organizationId}/semester-timelines",
    response_model=APIResponse[SemesterTimelineResponseSchema],
    summary="Create Semester Timeline",
    tags=["Academic Calendar Timelines"],
)
async def create_semester_timeline(
    organizationId: str,
    payload: SemesterTimelineCreateSchema,
    service: TimelineService = Depends(get_timeline_service),
    _: Any = Depends(check_permission("academic:write")),
):
    res = await service.create_semester_timeline(organizationId, payload.model_dump(by_alias=True))
    await _audit(res.organization_id, "timeline.semester_created", {"id": res.timeline_id, "semesterId": str(res.semester_id)})
    return APIResponse(success=True, message="Semester Timeline created successfully.", data=res)


@router.get(
    "/organizations/{organizationId}/semester-timelines",
    response_model=APIResponse[List[SemesterTimelineResponseSchema]],
    summary="List Semester Timelines",
    tags=["Academic Calendar Timelines"],
)
async def list_semester_timelines(
    organizationId: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    sortBy: str = Query("startDate"),
    sortOrder: str = Query("asc"),
    academicYearTimelineId: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    service: TimelineService = Depends(get_timeline_service),
    _: Any = Depends(get_current_identity),
):
    org_oid = await _get_org_oid(organizationId)
    filters = {}
    if academicYearTimelineId:
        filters["academicYearTimelineId"] = academicYearTimelineId
    if status:
        filters["status"] = status
    items = await service.semt_repo.list(org_oid, skip, limit, sortBy, sortOrder, filters)
    total = await service.semt_repo.count(org_oid, filters)
    return APIResponse(success=True, data=items, meta={"pagination": {"skip": skip, "limit": limit, "total": total}})


@router.get(
    "/organizations/{organizationId}/semester-timelines/{id}",
    response_model=APIResponse[SemesterTimelineResponseSchema],
    summary="Get Semester Timeline by ID",
    tags=["Academic Calendar Timelines"],
)
async def get_semester_timeline(
    organizationId: str,
    id: str,
    service: TimelineService = Depends(get_timeline_service),
    _: Any = Depends(get_current_identity),
):
    org_oid = await _get_org_oid(organizationId)
    res = await service.semt_repo.find_by_id(id, org_oid)
    return APIResponse(success=True, data=res)


@router.patch(
    "/organizations/{organizationId}/semester-timelines/{id}",
    response_model=APIResponse[SemesterTimelineResponseSchema],
    summary="Update Semester Timeline",
    tags=["Academic Calendar Timelines"],
)
async def update_semester_timeline(
    organizationId: str,
    id: str,
    payload: SemesterTimelineUpdateSchema,
    service: TimelineService = Depends(get_timeline_service),
    _: Any = Depends(check_permission("academic:write")),
):
    res = await service.update_semester_timeline(organizationId, id, payload.model_dump(exclude_unset=True, by_alias=True))
    await _audit(res.organization_id, "timeline.semester_updated", {"id": id})
    return APIResponse(success=True, message="Semester Timeline updated successfully.", data=res)


@router.delete(
    "/organizations/{organizationId}/semester-timelines/{id}",
    response_model=APIResponse[bool],
    summary="Delete Semester Timeline",
    tags=["Academic Calendar Timelines"],
)
async def delete_semester_timeline(
    organizationId: str,
    id: str,
    service: TimelineService = Depends(get_timeline_service),
    _: Any = Depends(check_permission("academic:delete")),
):
    org_oid = await _get_org_oid(organizationId)
    res = await service.semt_repo.find_by_id(id, org_oid)
    await service.delete_semester_timeline(organizationId, id)
    await _audit(res.organization_id, "timeline.semester_deleted", {"id": id})
    return APIResponse(success=True, message="Semester Timeline soft deleted.", data=True)


# ============================================================================
# HOLIDAYS
# ============================================================================

@router.post(
    "/organizations/{organizationId}/holidays",
    response_model=APIResponse[HolidayResponseSchema],
    summary="Create Holiday",
    tags=["Holidays"],
)
async def create_holiday(
    organizationId: str,
    payload: HolidayCreateSchema,
    service: HolidayService = Depends(get_holiday_service),
    _: Any = Depends(check_permission("academic:write")),
):
    res = await service.create_holiday(organizationId, payload.model_dump(by_alias=True))
    await _audit(res.organization_id, "holiday.created", {"id": res.holiday_id, "name": res.name})
    return APIResponse(success=True, message="Holiday created successfully.", data=res)


@router.get(
    "/organizations/{organizationId}/holidays",
    response_model=APIResponse[List[HolidayResponseSchema]],
    summary="List Holidays",
    tags=["Holidays"],
)
async def list_holidays(
    organizationId: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    sortBy: str = Query("date"),
    sortOrder: str = Query("asc"),
    calendarId: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    startDate: Optional[datetime] = Query(None),
    endDate: Optional[datetime] = Query(None),
    service: HolidayService = Depends(get_holiday_service),
    _: Any = Depends(get_current_identity),
):
    org_oid = await _get_org_oid(organizationId)
    filters = {}
    if calendarId:
        filters["calendarId"] = calendarId
    if type:
        filters["type"] = type
    if startDate:
        filters["startDate"] = startDate
    if endDate:
        filters["endDate"] = endDate
    items = await service.hol_repo.list(org_oid, skip, limit, sortBy, sortOrder, filters)
    total = await service.hol_repo.count(org_oid, filters)
    return APIResponse(success=True, data=items, meta={"pagination": {"skip": skip, "limit": limit, "total": total}})


@router.get(
    "/organizations/{organizationId}/holidays/{id}",
    response_model=APIResponse[HolidayResponseSchema],
    summary="Get Holiday by ID",
    tags=["Holidays"],
)
async def get_holiday(
    organizationId: str,
    id: str,
    service: HolidayService = Depends(get_holiday_service),
    _: Any = Depends(get_current_identity),
):
    org_oid = await _get_org_oid(organizationId)
    res = await service.hol_repo.find_by_id(id, org_oid)
    return APIResponse(success=True, data=res)


@router.patch(
    "/organizations/{organizationId}/holidays/{id}",
    response_model=APIResponse[HolidayResponseSchema],
    summary="Update Holiday",
    tags=["Holidays"],
)
async def update_holiday(
    organizationId: str,
    id: str,
    payload: HolidayUpdateSchema,
    service: HolidayService = Depends(get_holiday_service),
    _: Any = Depends(check_permission("academic:write")),
):
    res = await service.update_holiday(organizationId, id, payload.model_dump(exclude_unset=True, by_alias=True))
    await _audit(res.organization_id, "holiday.updated", {"id": id})
    return APIResponse(success=True, message="Holiday updated successfully.", data=res)


@router.delete(
    "/organizations/{organizationId}/holidays/{id}",
    response_model=APIResponse[bool],
    summary="Delete Holiday",
    tags=["Holidays"],
)
async def delete_holiday(
    organizationId: str,
    id: str,
    service: HolidayService = Depends(get_holiday_service),
    _: Any = Depends(check_permission("academic:delete")),
):
    org_oid = await _get_org_oid(organizationId)
    res = await service.hol_repo.find_by_id(id, org_oid)
    await service.delete_holiday(organizationId, id)
    await _audit(res.organization_id, "holiday.deleted", {"id": id})
    return APIResponse(success=True, message="Holiday deleted.", data=True)


# ============================================================================
# WORKING DAYS
# ============================================================================

@router.post(
    "/organizations/{organizationId}/working-days",
    response_model=APIResponse[WorkingDayResponseSchema],
    summary="Create Working Day Exception",
    tags=["Working Days"],
)
async def create_working_day(
    organizationId: str,
    payload: WorkingDayCreateSchema,
    service: HolidayService = Depends(get_holiday_service),
    _: Any = Depends(check_permission("academic:write")),
):
    res = await service.create_working_day(organizationId, payload.model_dump(by_alias=True))
    await _audit(res.organization_id, "working_day.created", {"id": res.working_day_id, "date": str(res.date)})
    return APIResponse(success=True, message="Working day exception created.", data=res)


@router.get(
    "/organizations/{organizationId}/working-days",
    response_model=APIResponse[List[WorkingDayResponseSchema]],
    summary="List Working Day Exceptions",
    tags=["Working Days"],
)
async def list_working_days(
    organizationId: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    calendarId: Optional[str] = Query(None),
    startDate: Optional[datetime] = Query(None),
    endDate: Optional[datetime] = Query(None),
    service: HolidayService = Depends(get_holiday_service),
    _: Any = Depends(get_current_identity),
):
    org_oid = await _get_org_oid(organizationId)
    filters = {}
    if calendarId:
        filters["calendarId"] = calendarId
    if startDate:
        filters["startDate"] = startDate
    if endDate:
        filters["endDate"] = endDate
    items = await service.wkd_repo.list(org_oid, skip, limit, "date", "asc", filters)
    total = await service.wkd_repo.count(org_oid, filters)
    return APIResponse(success=True, data=items, meta={"pagination": {"skip": skip, "limit": limit, "total": total}})


@router.delete(
    "/organizations/{organizationId}/working-days/{id}",
    response_model=APIResponse[bool],
    summary="Delete Working Day Exception",
    tags=["Working Days"],
)
async def delete_working_day(
    organizationId: str,
    id: str,
    service: HolidayService = Depends(get_holiday_service),
    _: Any = Depends(check_permission("academic:delete")),
):
    org_oid = await _get_org_oid(organizationId)
    res = await service.wkd_repo.find_by_id(id, org_oid)
    await service.delete_working_day(organizationId, id)
    await _audit(res.organization_id, "working_day.deleted", {"id": id})
    return APIResponse(success=True, message="Working day exception removed.", data=True)


# ============================================================================
# SCHEDULING WINDOWS
# ============================================================================

@router.post(
    "/organizations/{organizationId}/scheduling-windows",
    response_model=APIResponse[SchedulingWindowResponseSchema],
    summary="Create Scheduling Window",
    tags=["Scheduling Windows"],
)
async def create_scheduling_window(
    organizationId: str,
    payload: SchedulingWindowCreateSchema,
    service: WindowService = Depends(get_window_service),
    _: Any = Depends(check_permission("academic:write")),
):
    res = await service.create_scheduling_window(organizationId, payload.model_dump(by_alias=True))
    await _audit(res.organization_id, "window.created", {"id": res.window_id, "type": res.window_type})
    return APIResponse(success=True, message="Scheduling Window created successfully.", data=res)


@router.get(
    "/organizations/{organizationId}/scheduling-windows",
    response_model=APIResponse[List[SchedulingWindowResponseSchema]],
    summary="List Scheduling Windows",
    tags=["Scheduling Windows"],
)
async def list_scheduling_windows(
    organizationId: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    sortBy: str = Query("startDate"),
    sortOrder: str = Query("asc"),
    calendarId: Optional[str] = Query(None),
    semesterTimelineId: Optional[str] = Query(None),
    windowType: Optional[str] = Query(None),
    activityType: Optional[str] = Query(None),
    isActive: Optional[bool] = Query(None),
    service: WindowService = Depends(get_window_service),
    _: Any = Depends(get_current_identity),
):
    org_oid = await _get_org_oid(organizationId)
    filters = {}
    if calendarId:
        filters["calendarId"] = calendarId
    if semesterTimelineId:
        filters["semesterTimelineId"] = semesterTimelineId
    if windowType:
        filters["windowType"] = windowType
    if activityType:
        filters["activityType"] = activityType
    if isActive is not None:
        filters["isActive"] = isActive
    items = await service.win_repo.list(org_oid, skip, limit, sortBy, sortOrder, filters)
    total = await service.win_repo.count(org_oid, filters)
    return APIResponse(success=True, data=items, meta={"pagination": {"skip": skip, "limit": limit, "total": total}})


@router.get(
    "/organizations/{organizationId}/scheduling-windows/{id}",
    response_model=APIResponse[SchedulingWindowResponseSchema],
    summary="Get Scheduling Window by ID",
    tags=["Scheduling Windows"],
)
async def get_scheduling_window(
    organizationId: str,
    id: str,
    service: WindowService = Depends(get_window_service),
    _: Any = Depends(get_current_identity),
):
    org_oid = await _get_org_oid(organizationId)
    res = await service.win_repo.find_by_id(id, org_oid)
    return APIResponse(success=True, data=res)


@router.patch(
    "/organizations/{organizationId}/scheduling-windows/{id}",
    response_model=APIResponse[SchedulingWindowResponseSchema],
    summary="Update Scheduling Window",
    tags=["Scheduling Windows"],
)
async def update_scheduling_window(
    organizationId: str,
    id: str,
    payload: SchedulingWindowUpdateSchema,
    service: WindowService = Depends(get_window_service),
    _: Any = Depends(check_permission("academic:write")),
):
    res = await service.update_scheduling_window(organizationId, id, payload.model_dump(exclude_unset=True, by_alias=True))
    await _audit(res.organization_id, "window.updated", {"id": id})
    return APIResponse(success=True, message="Scheduling Window updated successfully.", data=res)


@router.delete(
    "/organizations/{organizationId}/scheduling-windows/{id}",
    response_model=APIResponse[bool],
    summary="Delete Scheduling Window",
    tags=["Scheduling Windows"],
)
async def delete_scheduling_window(
    organizationId: str,
    id: str,
    service: WindowService = Depends(get_window_service),
    _: Any = Depends(check_permission("academic:delete")),
):
    org_oid = await _get_org_oid(organizationId)
    res = await service.win_repo.find_by_id(id, org_oid)
    await service.delete_scheduling_window(organizationId, id)
    await _audit(res.organization_id, "window.deleted", {"id": id})
    return APIResponse(success=True, message="Scheduling Window deleted.", data=True)


# ============================================================================
# CALENDAR EVENTS (CUSTOM EVENTS)
# ============================================================================

@router.post(
    "/organizations/{organizationId}/calendar-events",
    response_model=APIResponse[CalendarEventResponseSchema],
    summary="Create Calendar Event",
    tags=["Calendar Events"],
)
async def create_calendar_event(
    organizationId: str,
    payload: CalendarEventCreateSchema,
    service: WindowService = Depends(get_window_service),
    _: Any = Depends(check_permission("academic:write")),
):
    res = await service.create_calendar_event(organizationId, payload.model_dump(by_alias=True))
    await _audit(res.organization_id, "calendar_event.created", {"id": res.event_id, "name": res.name})
    return APIResponse(success=True, message="Calendar Event created successfully.", data=res)


@router.get(
    "/organizations/{organizationId}/calendar-events",
    response_model=APIResponse[List[CalendarEventResponseSchema]],
    summary="List Calendar Events",
    tags=["Calendar Events"],
)
async def list_calendar_events(
    organizationId: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    sortBy: str = Query("startDate"),
    sortOrder: str = Query("asc"),
    calendarId: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    service: WindowService = Depends(get_window_service),
    _: Any = Depends(get_current_identity),
):
    org_oid = await _get_org_oid(organizationId)
    filters = {}
    if calendarId:
        filters["calendarId"] = calendarId
    if category:
        filters["category"] = category
    items = await service.cve_repo.list(org_oid, skip, limit, sortBy, sortOrder, filters)
    total = await service.cve_repo.count(org_oid, filters)
    return APIResponse(success=True, data=items, meta={"pagination": {"skip": skip, "limit": limit, "total": total}})


@router.delete(
    "/organizations/{organizationId}/calendar-events/{id}",
    response_model=APIResponse[bool],
    summary="Delete Calendar Event",
    tags=["Calendar Events"],
)
async def delete_calendar_event(
    organizationId: str,
    id: str,
    service: WindowService = Depends(get_window_service),
    _: Any = Depends(check_permission("academic:delete")),
):
    org_oid = await _get_org_oid(organizationId)
    res = await service.cve_repo.find_by_id(id, org_oid)
    await service.delete_calendar_event(organizationId, id)
    await _audit(res.organization_id, "calendar_event.deleted", {"id": id})
    return APIResponse(success=True, message="Calendar Event deleted.", data=True)


# ============================================================================
# UNIFIED TIMELINE & EXPORT (ICS) & ACTIVE CHECKERS
# ============================================================================

@router.get(
    "/organizations/{organizationId}/timeline",
    response_model=APIResponse[UnifiedTimelineResponseSchema],
    summary="Get Full Unified Calendar Timeline",
    tags=["Academic Calendar Timeline Console"],
)
async def get_unified_timeline(
    organizationId: str,
    service: WindowService = Depends(get_window_service),
    _: Any = Depends(get_current_identity),
):
    res = await service.get_unified_timeline(organizationId)
    return APIResponse(success=True, data=res)


@router.get(
    "/organizations/{organizationId}/timeline/export",
    summary="Export Active Timeline to standard iCal (ICS) format file",
    tags=["Academic Calendar Timeline Console"],
)
async def export_timeline_ics(
    organizationId: str,
    service: WindowService = Depends(get_window_service),
    _: Any = Depends(get_current_identity),
):
    ics_text = await service.export_timeline_ics(organizationId)
    return StreamingResponse(
        io.StringIO(ics_text),
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=academic_calendar.ics"}
    )


@router.get(
    "/organizations/{organizationId}/timeline/check-window",
    response_model=APIResponse[bool],
    summary="Verify if a Scheduling/Registration window is currently active",
    tags=["Academic Calendar Timeline Console"],
)
async def check_window_open(
    organizationId: str,
    windowType: WindowType = Query(..., alias="windowType"),
    activityType: str = Query(..., alias="activityType"),
    checkDate: Optional[datetime] = Query(None, alias="checkDate"),
    service: WindowService = Depends(get_window_service),
    _: Any = Depends(get_current_identity),
):
    is_open = await service.is_window_open(organizationId, windowType, activityType, checkDate)
    return APIResponse(success=True, data=is_open, message=f"Window of type {windowType} and activity {activityType} is {'open' if is_open else 'closed'}.")
