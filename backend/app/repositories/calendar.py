from typing import List, Optional, Tuple, Dict, Any
from beanie import PydanticObjectId
from pymongo.client_session import ClientSession
from pymongo import IndexModel
from datetime import datetime

from app.models.calendar import (
    AcademicCalendar,
    AcademicYearTimeline,
    SemesterTimeline,
    Holiday,
    WorkingDay,
    SchedulingWindow,
    CalendarEvent
)

class BaseCalendarRepository:
    """
    Base Repository containing shared utilities for mapping update properties
    and synchronizing internal attributes.
    """
    @staticmethod
    def sync_model(model: Any, update_fields: dict) -> None:
        # Build mapping from aliases/fieldnames to internal attribute name
        field_mapping = {}
        for name, field in model.model_fields.items():
            field_mapping[name] = name
            if field.alias:
                field_mapping[field.alias] = name

        # Sync in-memory model using mapped property names
        for k, v in update_fields.items():
            attr_name = field_mapping.get(k, k)
            if hasattr(model, attr_name):
                setattr(model, attr_name, v)

    @staticmethod
    def map_db_fields(model: Any, update_fields: dict) -> dict:
        db_fields = {}
        for name, field in model.model_fields.items():
            alias = field.alias or name
            db_fields[name] = alias
            if field.alias:
                db_fields[field.alias] = alias
        
        db_update_fields = {}
        for k, v in update_fields.items():
            db_alias = db_fields.get(k, k)
            db_update_fields[db_alias] = v
        return db_update_fields


class CalendarRepository(BaseCalendarRepository):
    async def create(self, cal: AcademicCalendar, session: Optional[ClientSession] = None) -> AcademicCalendar:
        return await cal.insert(session=session)

    async def update(self, cal: AcademicCalendar, update_fields: dict, session: Optional[ClientSession] = None) -> AcademicCalendar:
        for key in ["_id", "id", "calendar_id", "calendarId", "organization_id", "organizationId", "created_at"]:
            update_fields.pop(key, None)
        
        db_update = self.map_db_fields(cal, update_fields)
        await AcademicCalendar.find_one(AcademicCalendar.id == cal.id).update({"$set": db_update}, session=session)
        self.sync_model(cal, update_fields)
        return cal

    async def delete(self, cal: AcademicCalendar, session: Optional[ClientSession] = None) -> bool:
        await cal.soft_delete(session=session)
        return True

    async def find_by_id(self, cal_id: str, org_id: PydanticObjectId, session: Optional[ClientSession] = None) -> Optional[AcademicCalendar]:
        return await AcademicCalendar.find_one(
            AcademicCalendar.calendar_id == cal_id,
            AcademicCalendar.organization_id == org_id,
            AcademicCalendar.is_deleted == False,
            session=session
        )

    async def find_active_by_org(self, org_id: PydanticObjectId, session: Optional[ClientSession] = None) -> Optional[AcademicCalendar]:
        return await AcademicCalendar.find_one(
            AcademicCalendar.organization_id == org_id,
            AcademicCalendar.is_active == True,
            AcademicCalendar.is_deleted == False,
            session=session
        )

    async def list(
        self,
        org_id: PydanticObjectId,
        skip: int = 0,
        limit: int = 10,
        sort_by: str = "createdAt",
        sort_order: str = "asc",
        filters: Optional[dict] = None,
        session: Optional[ClientSession] = None
    ) -> List[AcademicCalendar]:
        sort_field_map = {"createdAt": "created_at", "name": "name"}
        internal_sort = sort_field_map.get(sort_by, "created_at")
        direction = -1 if sort_order.lower() == "desc" else 1

        query = [AcademicCalendar.organization_id == org_id, AcademicCalendar.is_deleted == False]
        if filters:
            if "status" in filters:
                query.append(AcademicCalendar.status == filters["status"])
            if "isActive" in filters:
                query.append(AcademicCalendar.is_active == filters["isActive"])

        cursor = AcademicCalendar.find(*query, session=session).sort([(internal_sort, direction)]).skip(skip).limit(limit)
        return await cursor.to_list()

    async def count(self, org_id: PydanticObjectId, filters: Optional[dict] = None, session: Optional[ClientSession] = None) -> int:
        query = [AcademicCalendar.organization_id == org_id, AcademicCalendar.is_deleted == False]
        if filters:
            if "status" in filters:
                query.append(AcademicCalendar.status == filters["status"])
            if "isActive" in filters:
                query.append(AcademicCalendar.is_active == filters["isActive"])
        return await AcademicCalendar.find(*query, session=session).count()

    async def exists(self, org_id: PydanticObjectId, name: str, session: Optional[ClientSession] = None) -> bool:
        doc = await AcademicCalendar.find_one(
            AcademicCalendar.organization_id == org_id,
            AcademicCalendar.name == name,
            AcademicCalendar.is_deleted == False,
            session=session
        )
        return doc is not None


class AcademicYearTimelineRepository(BaseCalendarRepository):
    async def create(self, timeline: AcademicYearTimeline, session: Optional[ClientSession] = None) -> AcademicYearTimeline:
        return await timeline.insert(session=session)

    async def update(self, timeline: AcademicYearTimeline, update_fields: dict, session: Optional[ClientSession] = None) -> AcademicYearTimeline:
        for key in ["_id", "id", "timeline_id", "timelineId", "organization_id", "organizationId", "calendar_id", "calendarId", "created_at"]:
            update_fields.pop(key, None)
        
        db_update = self.map_db_fields(timeline, update_fields)
        await AcademicYearTimeline.find_one(AcademicYearTimeline.id == timeline.id).update({"$set": db_update}, session=session)
        self.sync_model(timeline, update_fields)
        return timeline

    async def delete(self, timeline: AcademicYearTimeline, session: Optional[ClientSession] = None) -> bool:
        await timeline.soft_delete(session=session)
        return True

    async def find_by_id(self, timeline_id: str, org_id: PydanticObjectId, session: Optional[ClientSession] = None) -> Optional[AcademicYearTimeline]:
        return await AcademicYearTimeline.find_one(
            AcademicYearTimeline.timeline_id == timeline_id,
            AcademicYearTimeline.organization_id == org_id,
            AcademicYearTimeline.is_deleted == False,
            session=session
        )

    async def find_by_academic_year(self, acy_id: PydanticObjectId, calendar_id: PydanticObjectId, session: Optional[ClientSession] = None) -> Optional[AcademicYearTimeline]:
        return await AcademicYearTimeline.find_one(
            AcademicYearTimeline.academic_year_id == acy_id,
            AcademicYearTimeline.calendar_id == calendar_id,
            AcademicYearTimeline.is_deleted == False,
            session=session
        )

    async def list(
        self,
        org_id: PydanticObjectId,
        skip: int = 0,
        limit: int = 10,
        sort_by: str = "startDate",
        sort_order: str = "asc",
        filters: Optional[dict] = None,
        session: Optional[ClientSession] = None
    ) -> List[AcademicYearTimeline]:
        sort_field_map = {"startDate": "start_date", "endDate": "end_date", "createdAt": "created_at"}
        internal_sort = sort_field_map.get(sort_by, "start_date")
        direction = -1 if sort_order.lower() == "desc" else 1

        query = [AcademicYearTimeline.organization_id == org_id, AcademicYearTimeline.is_deleted == False]
        if filters:
            if "calendarId" in filters and filters["calendarId"]:
                query.append(AcademicYearTimeline.calendar_id == PydanticObjectId(filters["calendarId"]))
            if "status" in filters:
                query.append(AcademicYearTimeline.status == filters["status"])

        cursor = AcademicYearTimeline.find(*query, session=session).sort([(internal_sort, direction)]).skip(skip).limit(limit)
        return await cursor.to_list()

    async def count(self, org_id: PydanticObjectId, filters: Optional[dict] = None, session: Optional[ClientSession] = None) -> int:
        query = [AcademicYearTimeline.organization_id == org_id, AcademicYearTimeline.is_deleted == False]
        if filters:
            if "calendarId" in filters and filters["calendarId"]:
                query.append(AcademicYearTimeline.calendar_id == PydanticObjectId(filters["calendarId"]))
            if "status" in filters:
                query.append(AcademicYearTimeline.status == filters["status"])
        return await AcademicYearTimeline.find(*query, session=session).count()


class SemesterTimelineRepository(BaseCalendarRepository):
    async def create(self, timeline: SemesterTimeline, session: Optional[ClientSession] = None) -> SemesterTimeline:
        return await timeline.insert(session=session)

    async def update(self, timeline: SemesterTimeline, update_fields: dict, session: Optional[ClientSession] = None) -> SemesterTimeline:
        for key in ["_id", "id", "timeline_id", "timelineId", "organization_id", "organizationId", "academic_year_timeline_id", "academicYearTimelineId", "created_at"]:
            update_fields.pop(key, None)
        
        db_update = self.map_db_fields(timeline, update_fields)
        await SemesterTimeline.find_one(SemesterTimeline.id == timeline.id).update({"$set": db_update}, session=session)
        self.sync_model(timeline, update_fields)
        return timeline

    async def delete(self, timeline: SemesterTimeline, session: Optional[ClientSession] = None) -> bool:
        await timeline.soft_delete(session=session)
        return True

    async def find_by_id(self, timeline_id: str, org_id: PydanticObjectId, session: Optional[ClientSession] = None) -> Optional[SemesterTimeline]:
        return await SemesterTimeline.find_one(
            SemesterTimeline.timeline_id == timeline_id,
            SemesterTimeline.organization_id == org_id,
            SemesterTimeline.is_deleted == False,
            session=session
        )

    async def find_by_semester(self, sem_id: PydanticObjectId, timeline_acy_id: PydanticObjectId, session: Optional[ClientSession] = None) -> Optional[SemesterTimeline]:
        return await SemesterTimeline.find_one(
            SemesterTimeline.semester_id == sem_id,
            SemesterTimeline.academic_year_timeline_id == timeline_acy_id,
            SemesterTimeline.is_deleted == False,
            session=session
        )

    async def list(
        self,
        org_id: PydanticObjectId,
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "startDate",
        sort_order: str = "asc",
        filters: Optional[dict] = None,
        session: Optional[ClientSession] = None
    ) -> List[SemesterTimeline]:
        sort_field_map = {"startDate": "start_date", "endDate": "end_date", "createdAt": "created_at"}
        internal_sort = sort_field_map.get(sort_by, "start_date")
        direction = -1 if sort_order.lower() == "desc" else 1

        query = [SemesterTimeline.organization_id == org_id, SemesterTimeline.is_deleted == False]
        if filters:
            if "academicYearTimelineId" in filters and filters["academicYearTimelineId"]:
                query.append(SemesterTimeline.academic_year_timeline_id == PydanticObjectId(filters["academicYearTimelineId"]))
            if "status" in filters:
                query.append(SemesterTimeline.status == filters["status"])

        cursor = SemesterTimeline.find(*query, session=session).sort([(internal_sort, direction)]).skip(skip).limit(limit)
        return await cursor.to_list()

    async def count(self, org_id: PydanticObjectId, filters: Optional[dict] = None, session: Optional[ClientSession] = None) -> int:
        query = [SemesterTimeline.organization_id == org_id, SemesterTimeline.is_deleted == False]
        if filters:
            if "academicYearTimelineId" in filters and filters["academicYearTimelineId"]:
                query.append(SemesterTimeline.academic_year_timeline_id == PydanticObjectId(filters["academicYearTimelineId"]))
            if "status" in filters:
                query.append(SemesterTimeline.status == filters["status"])
        return await SemesterTimeline.find(*query, session=session).count()


class HolidayRepository(BaseCalendarRepository):
    async def create(self, holiday: Holiday, session: Optional[ClientSession] = None) -> Holiday:
        return await holiday.insert(session=session)

    async def update(self, holiday: Holiday, update_fields: dict, session: Optional[ClientSession] = None) -> Holiday:
        for key in ["_id", "id", "holiday_id", "holidayId", "organization_id", "organizationId", "calendar_id", "calendarId", "created_at"]:
            update_fields.pop(key, None)
        
        db_update = self.map_db_fields(holiday, update_fields)
        await Holiday.find_one(Holiday.id == holiday.id).update({"$set": db_update}, session=session)
        self.sync_model(holiday, update_fields)
        return holiday

    async def delete(self, holiday: Holiday, session: Optional[ClientSession] = None) -> bool:
        await holiday.soft_delete(session=session)
        return True

    async def find_by_id(self, holiday_id: str, org_id: PydanticObjectId, session: Optional[ClientSession] = None) -> Optional[Holiday]:
        return await Holiday.find_one(
            Holiday.holiday_id == holiday_id,
            Holiday.organization_id == org_id,
            Holiday.is_deleted == False,
            session=session
        )

    async def list(
        self,
        org_id: PydanticObjectId,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "date",
        sort_order: str = "asc",
        filters: Optional[dict] = None,
        session: Optional[ClientSession] = None
    ) -> List[Holiday]:
        sort_field_map = {"date": "date", "name": "name", "createdAt": "created_at"}
        internal_sort = sort_field_map.get(sort_by, "date")
        direction = -1 if sort_order.lower() == "desc" else 1

        query = [Holiday.organization_id == org_id, Holiday.is_deleted == False]
        if filters:
            if "calendarId" in filters and filters["calendarId"]:
                query.append(Holiday.calendar_id == PydanticObjectId(filters["calendarId"]))
            if "type" in filters:
                query.append(Holiday.type == filters["type"])
            if "startDate" in filters:
                query.append(Holiday.date >= filters["startDate"])
            if "endDate" in filters:
                query.append(Holiday.date <= filters["endDate"])

        cursor = Holiday.find(*query, session=session).sort([(internal_sort, direction)]).skip(skip).limit(limit)
        return await cursor.to_list()

    async def count(self, org_id: PydanticObjectId, filters: Optional[dict] = None, session: Optional[ClientSession] = None) -> int:
        query = [Holiday.organization_id == org_id, Holiday.is_deleted == False]
        if filters:
            if "calendarId" in filters and filters["calendarId"]:
                query.append(Holiday.calendar_id == PydanticObjectId(filters["calendarId"]))
            if "type" in filters:
                query.append(Holiday.type == filters["type"])
            if "startDate" in filters:
                query.append(Holiday.date >= filters["startDate"])
            if "endDate" in filters:
                query.append(Holiday.date <= filters["endDate"])
        return await Holiday.find(*query, session=session).count()


class WorkingDayRepository(BaseCalendarRepository):
    async def create(self, wkd: WorkingDay, session: Optional[ClientSession] = None) -> WorkingDay:
        return await wkd.insert(session=session)

    async def update(self, wkd: WorkingDay, update_fields: dict, session: Optional[ClientSession] = None) -> WorkingDay:
        for key in ["_id", "id", "working_day_id", "workingDayId", "organization_id", "organizationId", "calendar_id", "calendarId", "created_at"]:
            update_fields.pop(key, None)
        
        db_update = self.map_db_fields(wkd, update_fields)
        await WorkingDay.find_one(WorkingDay.id == wkd.id).update({"$set": db_update}, session=session)
        self.sync_model(wkd, update_fields)
        return wkd

    async def delete(self, wkd: WorkingDay, session: Optional[ClientSession] = None) -> bool:
        await wkd.soft_delete(session=session)
        return True

    async def find_by_id(self, working_day_id: str, org_id: PydanticObjectId, session: Optional[ClientSession] = None) -> Optional[WorkingDay]:
        return await WorkingDay.find_one(
            WorkingDay.working_day_id == working_day_id,
            WorkingDay.organization_id == org_id,
            WorkingDay.is_deleted == False,
            session=session
        )

    async def list(
        self,
        org_id: PydanticObjectId,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "date",
        sort_order: str = "asc",
        filters: Optional[dict] = None,
        session: Optional[ClientSession] = None
    ) -> List[WorkingDay]:
        sort_field_map = {"date": "date", "createdAt": "created_at"}
        internal_sort = sort_field_map.get(sort_by, "date")
        direction = -1 if sort_order.lower() == "desc" else 1

        query = [WorkingDay.organization_id == org_id, WorkingDay.is_deleted == False]
        if filters:
            if "calendarId" in filters and filters["calendarId"]:
                query.append(WorkingDay.calendar_id == PydanticObjectId(filters["calendarId"]))
            if "startDate" in filters:
                query.append(WorkingDay.date >= filters["startDate"])
            if "endDate" in filters:
                query.append(WorkingDay.date <= filters["endDate"])

        cursor = WorkingDay.find(*query, session=session).sort([(internal_sort, direction)]).skip(skip).limit(limit)
        return await cursor.to_list()

    async def count(self, org_id: PydanticObjectId, filters: Optional[dict] = None, session: Optional[ClientSession] = None) -> int:
        query = [WorkingDay.organization_id == org_id, WorkingDay.is_deleted == False]
        if filters:
            if "calendarId" in filters and filters["calendarId"]:
                query.append(WorkingDay.calendar_id == PydanticObjectId(filters["calendarId"]))
            if "startDate" in filters:
                query.append(WorkingDay.date >= filters["startDate"])
            if "endDate" in filters:
                query.append(WorkingDay.date <= filters["endDate"])
        return await WorkingDay.find(*query, session=session).count()


class SchedulingWindowRepository(BaseCalendarRepository):
    async def create(self, window: SchedulingWindow, session: Optional[ClientSession] = None) -> SchedulingWindow:
        return await window.insert(session=session)

    async def update(self, window: SchedulingWindow, update_fields: dict, session: Optional[ClientSession] = None) -> SchedulingWindow:
        for key in ["_id", "id", "window_id", "windowId", "organization_id", "organizationId", "calendar_id", "calendarId", "created_at"]:
            update_fields.pop(key, None)
        
        db_update = self.map_db_fields(window, update_fields)
        await SchedulingWindow.find_one(SchedulingWindow.id == window.id).update({"$set": db_update}, session=session)
        self.sync_model(window, update_fields)
        return window

    async def delete(self, window: SchedulingWindow, session: Optional[ClientSession] = None) -> bool:
        await window.soft_delete(session=session)
        return True

    async def find_by_id(self, window_id: str, org_id: PydanticObjectId, session: Optional[ClientSession] = None) -> Optional[SchedulingWindow]:
        return await SchedulingWindow.find_one(
            SchedulingWindow.window_id == window_id,
            SchedulingWindow.organization_id == org_id,
            SchedulingWindow.is_deleted == False,
            session=session
        )

    async def list(
        self,
        org_id: PydanticObjectId,
        skip: int = 0,
        limit: int = 50,
        sort_by: str = "startDate",
        sort_order: str = "asc",
        filters: Optional[dict] = None,
        session: Optional[ClientSession] = None
    ) -> List[SchedulingWindow]:
        sort_field_map = {"startDate": "start_date", "endDate": "end_date", "createdAt": "created_at", "name": "name"}
        internal_sort = sort_field_map.get(sort_by, "start_date")
        direction = -1 if sort_order.lower() == "desc" else 1

        query = [SchedulingWindow.organization_id == org_id, SchedulingWindow.is_deleted == False]
        if filters:
            if "calendarId" in filters and filters["calendarId"]:
                query.append(SchedulingWindow.calendar_id == PydanticObjectId(filters["calendarId"]))
            if "semesterTimelineId" in filters and filters["semesterTimelineId"]:
                query.append(SchedulingWindow.semester_timeline_id == PydanticObjectId(filters["semesterTimelineId"]))
            if "windowType" in filters:
                query.append(SchedulingWindow.window_type == filters["windowType"])
            if "activityType" in filters:
                query.append(SchedulingWindow.activity_type == filters["activityType"])
            if "isActive" in filters:
                query.append(SchedulingWindow.is_active == filters["isActive"])

        cursor = SchedulingWindow.find(*query, session=session).sort([(internal_sort, direction)]).skip(skip).limit(limit)
        return await cursor.to_list()

    async def count(self, org_id: PydanticObjectId, filters: Optional[dict] = None, session: Optional[ClientSession] = None) -> int:
        query = [SchedulingWindow.organization_id == org_id, SchedulingWindow.is_deleted == False]
        if filters:
            if "calendarId" in filters and filters["calendarId"]:
                query.append(SchedulingWindow.calendar_id == PydanticObjectId(filters["calendarId"]))
            if "semesterTimelineId" in filters and filters["semesterTimelineId"]:
                query.append(SchedulingWindow.semester_timeline_id == PydanticObjectId(filters["semesterTimelineId"]))
            if "windowType" in filters:
                query.append(SchedulingWindow.window_type == filters["windowType"])
            if "activityType" in filters:
                query.append(SchedulingWindow.activity_type == filters["activityType"])
            if "isActive" in filters:
                query.append(SchedulingWindow.is_active == filters["isActive"])
        return await SchedulingWindow.find(*query, session=session).count()


class CalendarEventRepository(BaseCalendarRepository):
    async def create(self, event: CalendarEvent, session: Optional[ClientSession] = None) -> CalendarEvent:
        return await event.insert(session=session)

    async def update(self, event: CalendarEvent, update_fields: dict, session: Optional[ClientSession] = None) -> CalendarEvent:
        for key in ["_id", "id", "event_id", "eventId", "organization_id", "organizationId", "calendar_id", "calendarId", "created_at"]:
            update_fields.pop(key, None)
        
        db_update = self.map_db_fields(event, update_fields)
        await CalendarEvent.find_one(CalendarEvent.id == event.id).update({"$set": db_update}, session=session)
        self.sync_model(event, update_fields)
        return event

    async def delete(self, event: CalendarEvent, session: Optional[ClientSession] = None) -> bool:
        await event.soft_delete(session=session)
        return True

    async def find_by_id(self, event_id: str, org_id: PydanticObjectId, session: Optional[ClientSession] = None) -> Optional[CalendarEvent]:
        return await CalendarEvent.find_one(
            CalendarEvent.event_id == event_id,
            CalendarEvent.organization_id == org_id,
            CalendarEvent.is_deleted == False,
            session=session
        )

    async def list(
        self,
        org_id: PydanticObjectId,
        skip: int = 0,
        limit: int = 50,
        sort_by: str = "startDate",
        sort_order: str = "asc",
        filters: Optional[dict] = None,
        session: Optional[ClientSession] = None
    ) -> List[CalendarEvent]:
        sort_field_map = {"startDate": "start_date", "endDate": "end_date", "createdAt": "created_at", "name": "name"}
        internal_sort = sort_field_map.get(sort_by, "start_date")
        direction = -1 if sort_order.lower() == "desc" else 1

        query = [CalendarEvent.organization_id == org_id, CalendarEvent.is_deleted == False]
        if filters:
            if "calendarId" in filters and filters["calendarId"]:
                query.append(CalendarEvent.calendar_id == PydanticObjectId(filters["calendarId"]))
            if "category" in filters:
                query.append(CalendarEvent.category == filters["category"])

        cursor = CalendarEvent.find(*query, session=session).sort([(internal_sort, direction)]).skip(skip).limit(limit)
        return await cursor.to_list()

    async def count(self, org_id: PydanticObjectId, filters: Optional[dict] = None, session: Optional[ClientSession] = None) -> int:
        query = [CalendarEvent.organization_id == org_id, CalendarEvent.is_deleted == False]
        if filters:
            if "calendarId" in filters and filters["calendarId"]:
                query.append(CalendarEvent.calendar_id == PydanticObjectId(filters["calendarId"]))
            if "category" in filters:
                query.append(CalendarEvent.category == filters["category"])
        return await CalendarEvent.find(*query, session=session).count()
