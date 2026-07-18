import pytest
from datetime import datetime
from beanie import PydanticObjectId

from app.models.calendar import (
    AcademicCalendar, AcademicYearTimeline, SemesterTimeline,
    Holiday, WorkingDay, SchedulingWindow, CalendarEvent,
    CalendarStatus, TimelineStatus, HolidayType, WindowType
)
from app.repositories.calendar import (
    CalendarRepository, AcademicYearTimelineRepository, SemesterTimelineRepository,
    HolidayRepository, WorkingDayRepository, SchedulingWindowRepository, CalendarEventRepository
)

pytestmark = pytest.mark.asyncio

async def test_calendar_repository_lifecycle():
    repo = CalendarRepository()
    org_id = PydanticObjectId()
    
    cal = AcademicCalendar(
        calendarId="CAL_000001",
        organizationId=org_id,
        name="Main Academic Calendar",
        timezone="Asia/Kolkata",
        isActive=True,
        status=CalendarStatus.ACTIVE
    )
    
    # Create
    await repo.create(cal)
    assert cal.id is not None
    
    # Find by ID
    found = await repo.find_by_id("CAL_000001", org_id)
    assert found is not None
    assert found.name == "Main Academic Calendar"
    assert found.timezone == "Asia/Kolkata"
    
    # Find active
    active = await repo.find_active_by_org(org_id)
    assert active is not None
    assert active.calendar_id == "CAL_000001"
    
    # Exists
    exists = await repo.exists(org_id, "Main Academic Calendar")
    assert exists is True
    
    # List and Count
    items = await repo.list(org_id)
    assert len(items) == 1
    cnt = await repo.count(org_id)
    assert cnt == 1
    
    # Update
    await repo.update(cal, {"name": "Revised Calendar"})
    assert cal.name == "Revised Calendar"
    
    # Delete
    await repo.delete(cal)
    assert cal.is_deleted is True
    
    found_after = await repo.find_by_id("CAL_000001", org_id)
    assert found_after is None


async def test_timeline_repository_lifecycle():
    cal_repo = CalendarRepository()
    acyt_repo = AcademicYearTimelineRepository()
    semt_repo = SemesterTimelineRepository()
    
    org_id = PydanticObjectId()
    cal_oid = PydanticObjectId()
    acy_oid = PydanticObjectId()
    sem_oid = PydanticObjectId()
    
    acyt = AcademicYearTimeline(
        timelineId="ACYT_000001",
        calendarId=cal_oid,
        academicYearId=acy_oid,
        organizationId=org_id,
        startDate=datetime(2026, 6, 1),
        endDate=datetime(2027, 5, 31),
        status=TimelineStatus.ACTIVE
    )
    
    await acyt_repo.create(acyt)
    assert acyt.id is not None
    
    found_acyt = await acyt_repo.find_by_id("ACYT_000001", org_id)
    assert found_acyt is not None
    assert found_acyt.timeline_id == "ACYT_000001"
    
    # Semester Timeline
    semt = SemesterTimeline(
        timelineId="SEMT_000001",
        academicYearTimelineId=acyt.id,
        semesterId=sem_oid,
        organizationId=org_id,
        startDate=datetime(2026, 6, 15),
        endDate=datetime(2026, 11, 30),
        status=TimelineStatus.ACTIVE
    )
    
    await semt_repo.create(semt)
    assert semt.id is not None
    
    found_semt = await semt_repo.find_by_id("SEMT_000001", org_id)
    assert found_semt is not None
    
    # Delete both
    await semt_repo.delete(semt)
    await acyt_repo.delete(acyt)
    assert semt.is_deleted is True
    assert acyt.is_deleted is True


async def test_holiday_working_day_repository_lifecycle():
    hol_repo = HolidayRepository()
    wkd_repo = WorkingDayRepository()
    
    org_id = PydanticObjectId()
    cal_oid = PydanticObjectId()
    
    hol = Holiday(
        holidayId="HOL_000001",
        calendarId=cal_oid,
        organizationId=org_id,
        name="New Year",
        date=datetime(2026, 1, 1),
        type=HolidayType.PUBLIC
    )
    
    await hol_repo.create(hol)
    assert hol.id is not None
    
    wkd = WorkingDay(
        workingDayId="WKD_000001",
        calendarId=cal_oid,
        organizationId=org_id,
        date=datetime(2026, 1, 3),
        description="Compensatory Saturday working day"
    )
    
    await wkd_repo.create(wkd)
    assert wkd.id is not None
    
    # List holidays
    hols = await hol_repo.list(org_id)
    assert len(hols) == 1
    
    # List working days
    wkds = await wkd_repo.list(org_id)
    assert len(wkds) == 1
    
    await hol_repo.delete(hol)
    await wkd_repo.delete(wkd)


async def test_scheduling_window_and_event_repository_lifecycle():
    win_repo = SchedulingWindowRepository()
    cve_repo = CalendarEventRepository()
    
    org_id = PydanticObjectId()
    cal_oid = PydanticObjectId()
    
    win = SchedulingWindow(
        windowId="WIN_000001",
        calendarId=cal_oid,
        organizationId=org_id,
        windowType=WindowType.REGISTRATION,
        activityType="EVENTS",
        name="Registration Window",
        startDate=datetime(2026, 6, 1),
        endDate=datetime(2026, 6, 15),
        isActive=True
    )
    
    await win_repo.create(win)
    assert win.id is not None
    
    cve = CalendarEvent(
        eventId="CVE_000001",
        calendarId=cal_oid,
        organizationId=org_id,
        name="Technical Fest",
        startDate=datetime(2026, 8, 10),
        endDate=datetime(2026, 8, 12),
        category="CULTURAL"
    )
    
    await cve_repo.create(cve)
    assert cve.id is not None
    
    # List windows
    wins = await win_repo.list(org_id)
    assert len(wins) == 1
    
    # List events
    events = await cve_repo.list(org_id)
    assert len(events) == 1
    
    await win_repo.delete(win)
    await cve_repo.delete(cve)
