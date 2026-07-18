from datetime import datetime
from typing import List, Optional, Tuple, Any
from beanie import PydanticObjectId
from pymongo.errors import PyMongoError

from app.core.database import get_db
from app.core.logger import logger
from app.repositories.organization import OrganizationRepository
from app.core.exceptions import OrganizationNotFound

from app.repositories.calendar import (
    CalendarRepository,
    AcademicYearTimelineRepository,
    SemesterTimelineRepository,
    HolidayRepository,
    WorkingDayRepository,
    SchedulingWindowRepository,
    CalendarEventRepository
)

from app.models.calendar import (
    AcademicCalendar,
    AcademicYearTimeline,
    SemesterTimeline,
    Holiday,
    WorkingDay,
    SchedulingWindow,
    CalendarEvent,
    CalendarStatus,
    TimelineStatus,
    HolidayType,
    WindowType
)

from app.calendar.exceptions import (
    CalendarNotFound,
    TimelineConflict,
    WindowOverlapException
)

class BaseCalendarService:
    def __init__(self):
        self.org_repo = OrganizationRepository()
        self.cal_repo = CalendarRepository()
        self.acyt_repo = AcademicYearTimelineRepository()
        self.semt_repo = SemesterTimelineRepository()
        self.hol_repo = HolidayRepository()
        self.wkd_repo = WorkingDayRepository()
        self.win_repo = SchedulingWindowRepository()
        self.cve_repo = CalendarEventRepository()

    async def _resolve_org(self, org_id_str: str) -> Any:
        org = await self.org_repo.find_by_id(org_id_str)
        if not org:
            raise OrganizationNotFound(f"Organization '{org_id_str}' not found.")
        return org

    async def _run_transactional(self, func, *args, **kwargs):
        """Run a coroutine inside a MongoDB transaction, with single-node fallback."""
        db = get_db()
        client = db.client
        try:
            async with await client.start_session() as session:
                async with session.start_transaction():
                    return await func(session, *args, **kwargs)
        except (PyMongoError, Exception) as e:
            if "replica set" in str(e).lower() or "transaction numbers" in str(e).lower():
                logger.warning("Transactions not supported — falling back to non-transactional execution.")
                return await func(None, *args, **kwargs)
            logger.error(f"Calendar transaction failure: {e}")
            raise


class CalendarService(BaseCalendarService):
    async def create_calendar(self, org_id_str: str, data: dict) -> AcademicCalendar:
        org = await self._resolve_org(org_id_str)
        count = await self.cal_repo.count(org.id)
        cal_id = f"CAL_{count + 1:06d}"
        
        cal = AcademicCalendar(
            calendarId=cal_id,
            organizationId=org.id,
            name=data["name"],
            timezone=data.get("timezone", "UTC"),
            weeklyWorkingDays=data.get("weeklyWorkingDays", [0, 1, 2, 3, 4]),
            isActive=False,
            status=CalendarStatus.DRAFT
        )
        return await self.cal_repo.create(cal)

    async def get_calendar(self, org_id_str: str, cal_id: str) -> AcademicCalendar:
        org = await self._resolve_org(org_id_str)
        cal = await self.cal_repo.find_by_id(cal_id, org.id)
        if not cal:
            raise CalendarNotFound(f"Calendar '{cal_id}' not found.")
        return cal

    async def list_calendars(self, org_id_str: str, skip: int = 0, limit: int = 10, sort_by: str = "createdAt", sort_order: str = "asc", filters: Optional[dict] = None) -> Tuple[List[AcademicCalendar], int]:
        org = await self._resolve_org(org_id_str)
        items = await self.cal_repo.list(org.id, skip, limit, sort_by, sort_order, filters)
        total = await self.cal_repo.count(org.id, filters)
        return items, total

    async def update_calendar(self, org_id_str: str, cal_id: str, data: dict) -> AcademicCalendar:
        org = await self._resolve_org(org_id_str)
        cal = await self.cal_repo.find_by_id(cal_id, org.id)
        if not cal:
            raise CalendarNotFound(f"Calendar '{cal_id}' not found.")
        return await self.cal_repo.update(cal, data)

    async def delete_calendar(self, org_id_str: str, cal_id: str) -> bool:
        org = await self._resolve_org(org_id_str)
        cal = await self.cal_repo.find_by_id(cal_id, org.id)
        if not cal:
            raise CalendarNotFound(f"Calendar '{cal_id}' not found.")
        await self.cal_repo.delete(cal)
        return True

    async def activate_calendar(self, org_id_str: str, cal_id: str) -> AcademicCalendar:
        org = await self._resolve_org(org_id_str)
        cal = await self.cal_repo.find_by_id(cal_id, org.id)
        if not cal:
            raise CalendarNotFound(f"Calendar '{cal_id}' not found.")
        
        async def _activate(session):
            await AcademicCalendar.find(
                AcademicCalendar.organization_id == org.id,
                AcademicCalendar.is_deleted == False,
                session=session
            ).update({"$set": {"isActive": False}}, session=session)
            
            cal.is_active = True
            cal.status = CalendarStatus.ACTIVE
            return await self.cal_repo.update(cal, {"isActive": True, "status": CalendarStatus.ACTIVE}, session=session)

        res = await self._run_transactional(_activate)
        return res


class TimelineService(BaseCalendarService):
    async def create_academic_year_timeline(self, org_id_str: str, data: dict) -> AcademicYearTimeline:
        org = await self._resolve_org(org_id_str)
        
        cal = await self.cal_repo.find_by_id(data["calendarId"], org.id)
        if not cal:
            raise CalendarNotFound(f"Calendar '{data['calendarId']}' not found.")
        
        from app.models.org_engine.academic import AcademicYear
        acy = await AcademicYear.find_one(
            AcademicYear.academic_year_id == data["academicYearId"],
            AcademicYear.organization_id == org.id,
            AcademicYear.is_deleted == False
        )
        if not acy:
            raise TimelineConflict(f"Academic year '{data['academicYearId']}' not found.")
        
        existing = await self.acyt_repo.find_by_academic_year(acy.id, cal.id)
        if existing:
            raise TimelineConflict(f"Timeline already configured for academic year '{data['academicYearId']}'.")
            
        count = await self.acyt_repo.count(org.id)
        timeline_id = f"ACYT_{count + 1:06d}"
        
        timeline = AcademicYearTimeline(
            timelineId=timeline_id,
            calendarId=cal.id,
            academicYearId=acy.id,
            organizationId=org.id,
            startDate=data["startDate"],
            endDate=data["endDate"],
            status=data.get("status", TimelineStatus.DRAFT)
        )
        return await self.acyt_repo.create(timeline)

    async def update_academic_year_timeline(self, org_id_str: str, timeline_id: str, data: dict) -> AcademicYearTimeline:
        org = await self._resolve_org(org_id_str)
        timeline = await self.acyt_repo.find_by_id(timeline_id, org.id)
        if not timeline:
            raise TimelineConflict(f"Academic Year Timeline '{timeline_id}' not found.")
        return await self.acyt_repo.update(timeline, data)

    async def delete_academic_year_timeline(self, org_id_str: str, timeline_id: str) -> bool:
        org = await self._resolve_org(org_id_str)
        timeline = await self.acyt_repo.find_by_id(timeline_id, org.id)
        if not timeline:
            raise TimelineConflict(f"Academic Year Timeline '{timeline_id}' not found.")
        await self.acyt_repo.delete(timeline)
        return True

    async def create_semester_timeline(self, org_id_str: str, data: dict) -> SemesterTimeline:
        org = await self._resolve_org(org_id_str)
        
        acyt = await self.acyt_repo.find_by_id(data["academicYearTimelineId"], org.id)
        if not acyt:
            raise TimelineConflict(f"Academic Year Timeline '{data['academicYearTimelineId']}' not found.")
            
        from app.models.org_engine.academic import Semester
        sem = await Semester.find_one(
            Semester.semester_id == data["semesterId"],
            Semester.organization_id == org.id,
            Semester.is_deleted == False
        )
        if not sem:
            raise TimelineConflict(f"Semester '{data['semesterId']}' not found.")
            
        existing = await self.semt_repo.find_by_semester(sem.id, acyt.id)
        if existing:
            raise TimelineConflict(f"Semester '{data['semesterId']}' timeline is already configured in this Academic Year Timeline.")

        start_date = data["startDate"]
        end_date = data["endDate"]
        if start_date < acyt.start_date or end_date > acyt.end_date:
            raise TimelineConflict(f"Semester timeline dates must fall within academic year timeline boundaries ({acyt.start_date} to {acyt.end_date}).")

        other_sems = await SemesterTimeline.find(
            SemesterTimeline.academic_year_timeline_id == acyt.id,
            SemesterTimeline.is_deleted == False
        ).to_list()
        
        for os in other_sems:
            if (start_date < os.end_date) and (end_date > os.start_date):
                raise TimelineConflict(f"Semester timeline dates overlap with another configured semester timeline (Timeline: {os.timeline_id}, Dates: {os.start_date} to {os.end_date}).")

        count = await self.semt_repo.count(org.id)
        timeline_id = f"SEMT_{count + 1:06d}"
        
        timeline = SemesterTimeline(
            timelineId=timeline_id,
            academicYearTimelineId=acyt.id,
            semesterId=sem.id,
            organizationId=org.id,
            startDate=start_date,
            endDate=end_date,
            status=data.get("status", TimelineStatus.DRAFT)
        )
        return await self.semt_repo.create(timeline)

    async def update_semester_timeline(self, org_id_str: str, timeline_id: str, data: dict) -> SemesterTimeline:
        org = await self._resolve_org(org_id_str)
        timeline = await self.semt_repo.find_by_id(timeline_id, org.id)
        if not timeline:
            raise TimelineConflict(f"Semester Timeline '{timeline_id}' not found.")
            
        start_date = data.get("startDate", timeline.start_date)
        end_date = data.get("endDate", timeline.end_date)
        
        if "startDate" in data or "endDate" in data:
            acyt = await AcademicYearTimeline.find_one(AcademicYearTimeline.id == timeline.academic_year_timeline_id)
            if acyt:
                if start_date < acyt.start_date or end_date > acyt.end_date:
                    raise TimelineConflict(f"Semester timeline dates must fall within academic year timeline boundaries ({acyt.start_date} to {acyt.end_date}).")

                other_sems = await SemesterTimeline.find(
                    SemesterTimeline.academic_year_timeline_id == acyt.id,
                    SemesterTimeline.id != timeline.id,
                    SemesterTimeline.is_deleted == False
                ).to_list()
                
                for os in other_sems:
                    if (start_date < os.end_date) and (end_date > os.start_date):
                        raise TimelineConflict(f"Semester timeline dates overlap with another configured semester timeline ({os.start_date} to {os.end_date}).")

        return await self.semt_repo.update(timeline, data)

    async def delete_semester_timeline(self, org_id_str: str, timeline_id: str) -> bool:
        org = await self._resolve_org(org_id_str)
        timeline = await self.semt_repo.find_by_id(timeline_id, org.id)
        if not timeline:
            raise TimelineConflict(f"Semester Timeline '{timeline_id}' not found.")
        await self.semt_repo.delete(timeline)
        return True


class HolidayService(BaseCalendarService):
    async def create_holiday(self, org_id_str: str, data: dict) -> Holiday:
        org = await self._resolve_org(org_id_str)
        cal = await self.cal_repo.find_by_id(data["calendarId"], org.id)
        if not cal:
            raise CalendarNotFound(f"Calendar '{data['calendarId']}' not found.")
            
        count = await self.hol_repo.count(org.id)
        holiday_id = f"HOL_{count + 1:06d}"
        
        holiday = Holiday(
            holidayId=holiday_id,
            calendarId=cal.id,
            organizationId=org.id,
            name=data["name"],
            date=data["date"],
            type=data.get("type", HolidayType.PUBLIC),
            description=data.get("description")
        )
        return await self.hol_repo.create(holiday)

    async def update_holiday(self, org_id_str: str, holiday_id: str, data: dict) -> Holiday:
        org = await self._resolve_org(org_id_str)
        holiday = await self.hol_repo.find_by_id(holiday_id, org.id)
        if not holiday:
            raise CalendarNotFound(f"Holiday '{holiday_id}' not found.")
        return await self.hol_repo.update(holiday, data)

    async def delete_holiday(self, org_id_str: str, holiday_id: str) -> bool:
        org = await self._resolve_org(org_id_str)
        holiday = await self.hol_repo.find_by_id(holiday_id, org.id)
        if not holiday:
            raise CalendarNotFound(f"Holiday '{holiday_id}' not found.")
        await self.hol_repo.delete(holiday)
        return True

    async def create_working_day(self, org_id_str: str, data: dict) -> WorkingDay:
        org = await self._resolve_org(org_id_str)
        cal = await self.cal_repo.find_by_id(data["calendarId"], org.id)
        if not cal:
            raise CalendarNotFound(f"Calendar '{data['calendarId']}' not found.")
            
        count = await self.wkd_repo.count(org.id)
        working_day_id = f"WKD_{count + 1:06d}"
        
        wkd = WorkingDay(
            workingDayId=working_day_id,
            calendarId=cal.id,
            organizationId=org.id,
            date=data["date"],
            description=data.get("description")
        )
        return await self.wkd_repo.create(wkd)

    async def update_working_day(self, org_id_str: str, working_day_id: str, data: dict) -> WorkingDay:
        org = await self._resolve_org(org_id_str)
        wkd = await self.wkd_repo.find_by_id(working_day_id, org.id)
        if not wkd:
            raise CalendarNotFound(f"Working day exception '{working_day_id}' not found.")
        return await self.wkd_repo.update(wkd, data)

    async def delete_working_day(self, org_id_str: str, working_day_id: str) -> bool:
        org = await self._resolve_org(org_id_str)
        wkd = await self.wkd_repo.find_by_id(working_day_id, org.id)
        if not wkd:
            raise CalendarNotFound(f"Working day exception '{working_day_id}' not found.")
        await self.wkd_repo.delete(wkd)
        return True

    async def is_working_day(self, org_id_str: str, date: datetime) -> bool:
        org = await self._resolve_org(org_id_str)
        cal = await self.cal_repo.find_active_by_org(org.id)
        if not cal:
            return True
            
        start_of_day = datetime(date.year, date.month, date.day)
        end_of_day = datetime(date.year, date.month, date.day, 23, 59, 59)
        
        holiday = await Holiday.find_one(
            Holiday.calendar_id == cal.id,
            Holiday.date >= start_of_day,
            Holiday.date <= end_of_day,
            Holiday.is_deleted == False
        )
        if holiday:
            return False
            
        wkd = await WorkingDay.find_one(
            WorkingDay.calendar_id == cal.id,
            WorkingDay.date >= start_of_day,
            WorkingDay.date <= end_of_day,
            WorkingDay.is_deleted == False
        )
        if wkd:
            return True
            
        weekday = date.weekday()
        return weekday in cal.weekly_working_days


class WindowService(BaseCalendarService):
    async def create_scheduling_window(self, org_id_str: str, data: dict) -> SchedulingWindow:
        org = await self._resolve_org(org_id_str)
        cal = await self.cal_repo.find_by_id(data["calendarId"], org.id)
        if not cal:
            raise CalendarNotFound(f"Calendar '{data['calendarId']}' not found.")
            
        sem_timeline_id = None
        if data.get("semesterTimelineId"):
            sem_t = await self.semt_repo.find_by_id(data["semesterTimelineId"], org.id)
            if not sem_t:
                raise TimelineConflict("Referenced semester timeline not found.")
            sem_timeline_id = sem_t.id
            
        start_date = data["startDate"]
        end_date = data["endDate"]
        window_type = data["windowType"]
        activity_type = data["activityType"]
        
        if window_type == WindowType.REGISTRATION:
            query = [
                SchedulingWindow.organization_id == org.id,
                SchedulingWindow.window_type == WindowType.REGISTRATION,
                SchedulingWindow.activity_type == activity_type,
                SchedulingWindow.is_active == True,
                SchedulingWindow.is_deleted == False
            ]
            if sem_timeline_id:
                query.append(SchedulingWindow.semester_timeline_id == sem_timeline_id)
            
            existing_windows = await SchedulingWindow.find(*query).to_list()
            for ew in existing_windows:
                if (start_date < ew.end_date) and (end_date > ew.start_date):
                    raise WindowOverlapException(f"Registration window overlaps with another active window for the same activity type.")

        count = await self.win_repo.count(org.id)
        window_id = f"WIN_{count + 1:06d}"
        
        window = SchedulingWindow(
            windowId=window_id,
            calendarId=cal.id,
            organizationId=org.id,
            semesterTimelineId=sem_timeline_id,
            windowType=window_type,
            activityType=activity_type,
            name=data["name"],
            startDate=start_date,
            endDate=end_date,
            isActive=data.get("isActive", True)
        )
        return await self.win_repo.create(window)

    async def update_scheduling_window(self, org_id_str: str, window_id: str, data: dict) -> SchedulingWindow:
        org = await self._resolve_org(org_id_str)
        window = await self.win_repo.find_by_id(window_id, org.id)
        if not window:
            raise CalendarNotFound(f"Scheduling window '{window_id}' not found.")
            
        start_date = data.get("startDate", window.start_date)
        end_date = data.get("endDate", window.end_date)
        window_type = data.get("windowType", window.window_type)
        activity_type = data.get("activityType", window.activity_type)
        sem_timeline_id = window.semester_timeline_id
        
        if "semesterTimelineId" in data:
            if data["semesterTimelineId"]:
                sem_t = await self.semt_repo.find_by_id(data["semesterTimelineId"], org.id)
                if not sem_t:
                    raise TimelineConflict("Referenced semester timeline not found.")
                sem_timeline_id = sem_t.id
            else:
                sem_timeline_id = None
                
        if window_type == WindowType.REGISTRATION and ("startDate" in data or "endDate" in data or "windowType" in data or "activityType" in data or "isActive" in data):
            is_active = data.get("isActive", window.is_active)
            if is_active:
                query = [
                    SchedulingWindow.organization_id == org.id,
                    SchedulingWindow.id != window.id,
                    SchedulingWindow.window_type == WindowType.REGISTRATION,
                    SchedulingWindow.activity_type == activity_type,
                    SchedulingWindow.is_active == True,
                    SchedulingWindow.is_deleted == False
                ]
                if sem_timeline_id:
                    query.append(SchedulingWindow.semester_timeline_id == sem_timeline_id)
                
                existing_windows = await SchedulingWindow.find(*query).to_list()
                for ew in existing_windows:
                    if (start_date < ew.end_date) and (end_date > ew.start_date):
                        raise WindowOverlapException(f"Registration window overlaps with another active window for the same activity type.")

        if "semesterTimelineId" in data:
            data["semesterTimelineId"] = sem_timeline_id

        return await self.win_repo.update(window, data)

    async def delete_scheduling_window(self, org_id_str: str, window_id: str) -> bool:
        org = await self._resolve_org(org_id_str)
        window = await self.win_repo.find_by_id(window_id, org.id)
        if not window:
            raise CalendarNotFound(f"Scheduling window '{window_id}' not found.")
        await self.win_repo.delete(window)
        return True

    async def create_calendar_event(self, org_id_str: str, data: dict) -> CalendarEvent:
        org = await self._resolve_org(org_id_str)
        cal = await self.cal_repo.find_by_id(data["calendarId"], org.id)
        if not cal:
            raise CalendarNotFound(f"Calendar '{data['calendarId']}' not found.")
            
        count = await self.cve_repo.count(org.id)
        event_id = f"CVE_{count + 1:06d}"
        
        event = CalendarEvent(
            eventId=event_id,
            calendarId=cal.id,
            organizationId=org.id,
            name=data["name"],
            startDate=data["startDate"],
            endDate=data["endDate"],
            description=data.get("description"),
            category=data.get("category", "ACADEMIC")
        )
        return await self.cve_repo.create(event)

    async def update_calendar_event(self, org_id_str: str, event_id: str, data: dict) -> CalendarEvent:
        org = await self._resolve_org(org_id_str)
        event = await self.cve_repo.find_by_id(event_id, org.id)
        if not event:
            raise CalendarNotFound(f"Calendar Event '{event_id}' not found.")
        return await self.cve_repo.update(event, data)

    async def delete_calendar_event(self, org_id_str: str, event_id: str) -> bool:
        org = await self._resolve_org(org_id_str)
        event = await self.cve_repo.find_by_id(event_id, org.id)
        if not event:
            raise CalendarNotFound(f"Calendar Event '{event_id}' not found.")
        await self.cve_repo.delete(event)
        return True

    async def is_window_open(
        self,
        org_id_str: str,
        window_type: WindowType,
        activity_type: str,
        check_date: Optional[datetime] = None
    ) -> bool:
        org = await self._resolve_org(org_id_str)
        cal = await self.cal_repo.find_active_by_org(org.id)
        if not cal:
            return False
            
        target_date = check_date or datetime.utcnow()
        
        window = await SchedulingWindow.find_one(
            SchedulingWindow.calendar_id == cal.id,
            SchedulingWindow.window_type == window_type,
            SchedulingWindow.activity_type == activity_type,
            SchedulingWindow.start_date <= target_date,
            SchedulingWindow.end_date >= target_date,
            SchedulingWindow.is_active == True,
            SchedulingWindow.is_deleted == False
        )
        return window is not None

    async def get_unified_timeline(self, org_id_str: str) -> dict:
        org = await self._resolve_org(org_id_str)
        active_cal = await self.cal_repo.find_active_by_org(org.id)
        
        if not active_cal:
            return {
                "activeCalendar": None,
                "academicYearTimelines": [],
                "semesterTimelines": [],
                "holidays": [],
                "workingDays": [],
                "schedulingWindows": [],
                "calendarEvents": []
            }
            
        acyt = await AcademicYearTimeline.find(
            AcademicYearTimeline.calendar_id == active_cal.id,
            AcademicYearTimeline.is_deleted == False
        ).to_list()
        
        acyt_ids = [t.id for t in acyt]
        
        semt = await SemesterTimeline.find(
            {"academicYearTimelineId": {"$in": acyt_ids}},
            SemesterTimeline.is_deleted == False
        ).to_list()
        
        hol = await Holiday.find(
            Holiday.calendar_id == active_cal.id,
            Holiday.is_deleted == False
        ).to_list()
        
        wkd = await WorkingDay.find(
            WorkingDay.calendar_id == active_cal.id,
            WorkingDay.is_deleted == False
        ).to_list()
        
        win = await SchedulingWindow.find(
            SchedulingWindow.calendar_id == active_cal.id,
            SchedulingWindow.is_deleted == False
        ).to_list()
        
        cve = await CalendarEvent.find(
            CalendarEvent.calendar_id == active_cal.id,
            CalendarEvent.is_deleted == False
        ).to_list()
        
        return {
            "activeCalendar": active_cal,
            "academicYearTimelines": acyt,
            "semesterTimelines": semt,
            "holidays": hol,
            "workingDays": wkd,
            "schedulingWindows": win,
            "calendarEvents": cve
        }

    async def export_timeline_ics(self, org_id_str: str) -> str:
        org = await self._resolve_org(org_id_str)
        timeline = await self.get_unified_timeline(org_id_str)
        
        active_cal = timeline["activeCalendar"]
        if not active_cal:
            return "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//CampusOS//Academic Calendar Engine//EN\nEND:VCALENDAR"
            
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//CampusOS//Academic Calendar Engine//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            f"X-WR-CALNAME:{active_cal.name} Academic Timeline",
            f"X-WR-TIMEZONE:{active_cal.timezone}"
        ]
        
        def format_dt(dt: datetime) -> str:
            return dt.strftime("%Y%m%dT%H%M%SZ")
            
        dtstamp = format_dt(datetime.utcnow())
        
        def add_event(uid_prefix: str, identifier: str, summary: str, start: datetime, end: datetime, desc: str = ""):
            lines.append("BEGIN:VEVENT")
            lines.append(f"UID:{uid_prefix}_{identifier}@campusos.com")
            lines.append(f"DTSTAMP:{dtstamp}")
            lines.append(f"DTSTART:{format_dt(start)}")
            lines.append(f"DTEND:{format_dt(end)}")
            lines.append(f"SUMMARY:{summary}")
            if desc:
                escaped_desc = desc.replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")
                lines.append(f"DESCRIPTION:{escaped_desc}")
            lines.append("END:VEVENT")

        for t in timeline["academicYearTimelines"]:
            add_event("acyt", t.timeline_id, f"Academic Year Timeline: {t.timeline_id}", t.start_date, t.end_date, f"Status: {t.status}")
            
        for t in timeline["semesterTimelines"]:
            add_event("semt", t.timeline_id, f"Semester Timeline: {t.timeline_id}", t.start_date, t.end_date, f"Status: {t.status}")
            
        for h in timeline["holidays"]:
            end_date = h.date.replace(hour=23, minute=59, second=59)
            add_event("hol", h.holiday_id, f"Holiday: {h.name} ({h.type})", h.date, end_date, h.description or "")
            
        for w in timeline["workingDays"]:
            end_date = w.date.replace(hour=23, minute=59, second=59)
            add_event("wkd", w.working_day_id, f"Working Day Exception", w.date, end_date, w.description or "")
            
        for w in timeline["schedulingWindows"]:
            add_event("win", w.window_id, f"Window ({w.window_type}): {w.name}", w.start_date, w.end_date, f"Activity: {w.activity_type}, Active: {w.is_active}")
            
        for e in timeline["calendarEvents"]:
            add_event("cve", e.event_id, f"Event ({e.category}): {e.name}", e.start_date, e.end_date, e.description or "")
            
        lines.append("END:VCALENDAR")
        return "\n".join(lines)
