import pytest
from datetime import datetime
from beanie import PydanticObjectId

from app.models.org_engine.organization import Organization
from app.models.org_engine.academic import AcademicYear, Semester
from app.models.calendar import CalendarStatus, TimelineStatus, HolidayType, WindowType
from app.calendar.service import (
    CalendarService, TimelineService, HolidayService, WindowService
)
from app.calendar.exceptions import (
    CalendarNotFound, TimelineConflict, WindowOverlapException
)

pytestmark = pytest.mark.asyncio

async def test_calendar_service_invariants():
    # Setup Organization
    org = Organization(
        organizationId="ORG_000001",
        name="Test University 1",
        shortName="Test Uni 1",
        slug="test-uni-1",
        emailDomain="test1.edu",
        contactEmail="admin@test1.edu"
    )
    await org.insert()
    
    cal_svc = CalendarService()
    
    # 1. Create multiple calendars
    cal1 = await cal_svc.create_calendar("ORG_000001", {"name": "Cal 1"})
    cal2 = await cal_svc.create_calendar("ORG_000001", {"name": "Cal 2"})
    
    assert cal1.is_active is False
    assert cal2.is_active is False
    
    # 2. Activate cal 1
    activated_cal1 = await cal_svc.activate_calendar("ORG_000001", cal1.calendar_id)
    assert activated_cal1.is_active is True
    
    # 3. Activate cal 2 -> cal 1 should become inactive
    activated_cal2 = await cal_svc.activate_calendar("ORG_000001", cal2.calendar_id)
    assert activated_cal2.is_active is True
    
    refreshed_cal1 = await cal_svc.get_calendar("ORG_000001", cal1.calendar_id)
    assert refreshed_cal1.is_active is False


async def test_semester_timeline_overlap():
    org = Organization(
        organizationId="ORG_000002",
        name="Test University 2",
        shortName="Test Uni 2",
        slug="test-uni-2",
        emailDomain="test2.edu",
        contactEmail="admin@test2.edu"
    )
    await org.insert()
    
    cal_svc = CalendarService()
    cal = await cal_svc.create_calendar("ORG_000002", {"name": "Cal"})
    await cal_svc.activate_calendar("ORG_000002", cal.calendar_id)
    
    acy = AcademicYear(
        academicYearId="ACY_000001",
        organizationId=org.id,
        name="2026-2027",
        startDate=datetime(2026, 6, 1),
        endDate=datetime(2027, 5, 31)
    )
    await acy.insert()
    
    sem1 = Semester(
        semesterId="SEM_000001",
        organizationId=org.id,
        number=1,
        name="Semester 1"
    )
    await sem1.insert()
    
    sem2 = Semester(
        semesterId="SEM_000002",
        organizationId=org.id,
        number=2,
        name="Semester 2"
    )
    await sem2.insert()
    
    timeline_svc = TimelineService()
    
    # Create Year Timeline
    acyt = await timeline_svc.create_academic_year_timeline("ORG_000002", {
        "calendarId": cal.calendar_id,
        "academicYearId": acy.academic_year_id,
        "startDate": datetime(2026, 6, 1),
        "endDate": datetime(2027, 5, 31)
    })
    
    # Create Sem 1 Timeline
    semt1 = await timeline_svc.create_semester_timeline("ORG_000002", {
        "academicYearTimelineId": acyt.timeline_id,
        "semesterId": sem1.semester_id,
        "startDate": datetime(2026, 6, 1),
        "endDate": datetime(2026, 11, 30)
    })
    
    # Overlapping Semester Timeline -> should fail
    with pytest.raises(TimelineConflict):
        await timeline_svc.create_semester_timeline("ORG_000002", {
            "academicYearTimelineId": acyt.timeline_id,
            "semesterId": sem2.semester_id,
            "startDate": datetime(2026, 10, 1),
            "endDate": datetime(2027, 3, 31)
        })
        
    # Non-overlapping Semester Timeline -> should pass
    semt2 = await timeline_svc.create_semester_timeline("ORG_000002", {
        "academicYearTimelineId": acyt.timeline_id,
        "semesterId": sem2.semester_id,
        "startDate": datetime(2026, 12, 1),
        "endDate": datetime(2027, 5, 31)
    })
    assert semt2.id is not None


async def test_holiday_and_working_day_exceptions():
    org = Organization(
        organizationId="ORG_000003",
        name="Test University 3",
        shortName="Test Uni 3",
        slug="test-uni-3",
        emailDomain="test3.edu",
        contactEmail="admin@test3.edu"
    )
    await org.insert()
    
    cal_svc = CalendarService()
    # Weekly working days: Monday=0 to Friday=4
    cal = await cal_svc.create_calendar("ORG_000003", {
        "name": "Cal 3",
        "weeklyWorkingDays": [0, 1, 2, 3, 4]
    })
    await cal_svc.activate_calendar("ORG_000003", cal.calendar_id)
    
    hol_svc = HolidayService()
    
    # 2026-01-01 is a Thursday (normally a working day)
    thursday = datetime(2026, 1, 1)
    assert await hol_svc.is_working_day("ORG_000003", thursday) is True
    
    # Register as Holiday
    await hol_svc.create_holiday("ORG_000003", {
        "calendarId": cal.calendar_id,
        "name": "New Year Day",
        "date": thursday,
        "type": HolidayType.PUBLIC
    })
    assert await hol_svc.is_working_day("ORG_000003", thursday) is False
    
    # 2026-01-03 is a Saturday (normally a weekend, non-working day)
    saturday = datetime(2026, 1, 3)
    assert await hol_svc.is_working_day("ORG_000003", saturday) is False
    
    # Register as Working Day override exception
    await hol_svc.create_working_day("ORG_000003", {
        "calendarId": cal.calendar_id,
        "date": saturday,
        "description": "Compensatory work Saturday"
    })
    assert await hol_svc.is_working_day("ORG_000003", saturday) is True


async def test_window_registration_overlap_and_check():
    org = Organization(
        organizationId="ORG_000004",
        name="Test University 4",
        shortName="Test Uni 4",
        slug="test-uni-4",
        emailDomain="test4.edu",
        contactEmail="admin@test4.edu"
    )
    await org.insert()
    
    cal_svc = CalendarService()
    cal = await cal_svc.create_calendar("ORG_000004", {"name": "Cal 4"})
    await cal_svc.activate_calendar("ORG_000004", cal.calendar_id)
    
    win_svc = WindowService()
    
    # Create standard registration window
    win1 = await win_svc.create_scheduling_window("ORG_000004", {
        "calendarId": cal.calendar_id,
        "windowType": WindowType.REGISTRATION,
        "activityType": "COURSES",
        "name": "Course Registration 1",
        "startDate": datetime(2026, 6, 1),
        "endDate": datetime(2026, 6, 10)
    })
    assert win1.id is not None
    
    # Registering overlapping registration window for COURSES -> should fail
    with pytest.raises(WindowOverlapException):
        await win_svc.create_scheduling_window("ORG_000004", {
            "calendarId": cal.calendar_id,
            "windowType": WindowType.REGISTRATION,
            "activityType": "COURSES",
            "name": "Course Registration Overlap",
            "startDate": datetime(2026, 6, 5),
            "endDate": datetime(2026, 6, 15)
        })
        
    # Check open window checker
    assert await win_svc.is_window_open("ORG_000004", WindowType.REGISTRATION, "COURSES", datetime(2026, 6, 5)) is True
    assert await win_svc.is_window_open("ORG_000004", WindowType.REGISTRATION, "COURSES", datetime(2026, 6, 12)) is False
