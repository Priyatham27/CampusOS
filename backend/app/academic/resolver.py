from typing import Optional, Any
from beanie import PydanticObjectId

from app.models.org_engine.academic import AcademicYear, Semester, Department, Branch, Section
from app.models.org_engine.curriculum import Program, Course
from app.models.calendar import AcademicCalendar
from app.academic.context import AcademicContext
from app.academic.cache import AcademicCacheLayer

class AcademicResolver:
    """
    Resolves academic entities from request context (headers, parameters)
    and populates the AcademicContext wrapper, utilizing cache layers.
    """
    def __init__(self):
        self.cache = AcademicCacheLayer()

    def _safe_object_id(self, val: str) -> Optional[PydanticObjectId]:
        try:
            return PydanticObjectId(val) if len(val) == 24 else None
        except Exception:
            return None

    async def resolve_academic_context(self, org_id: PydanticObjectId, headers: dict) -> AcademicContext:
        import time
        start_time = time.time()
        context = AcademicContext()
        
        # 1. Resolve Active Calendar
        cache_key = f"active_cal:{org_id}"
        cal = await self.cache.get(cache_key, AcademicCalendar)
        if not cal:
            cal = await AcademicCalendar.find_one(
                AcademicCalendar.organization_id == org_id,
                AcademicCalendar.is_active == True,
                AcademicCalendar.is_deleted == False
            )
            if cal:
                await self.cache.set(cache_key, cal, ttl=300)
        context.active_calendar = cal

        # Helper method for resolving single academic entities
        async def resolve_entity(model_cls, cache_prefix, header_val, id_field):
            if not header_val:
                return None
            
            ent_cache_key = f"{cache_prefix}:{org_id}:{header_val}"
            ent = await self.cache.get(ent_cache_key, model_cls)
            if not ent:
                obj_id = self._safe_object_id(header_val)
                query = [model_cls.organization_id == org_id, model_cls.is_deleted == False]
                
                if obj_id:
                    query.append(model_cls.id == obj_id)
                else:
                    query.append(getattr(model_cls, id_field) == header_val)

                ent = await model_cls.find_one(*query)
                if ent:
                    await self.cache.set(ent_cache_key, ent, ttl=300)
            return ent

        # 2. Resolve Academic Year
        ay_header = headers.get("x-academic-year-id") or headers.get("X-Academic-Year-ID")
        context.academic_year = await resolve_entity(AcademicYear, "ay", ay_header, "academic_year_id")

        # 3. Resolve Semester
        sem_header = headers.get("x-semester-id") or headers.get("X-Semester-ID")
        context.semester = await resolve_entity(Semester, "sem", sem_header, "semester_id")

        #  department
        dept_header = headers.get("x-department-id") or headers.get("X-Department-ID")
        context.department = await resolve_entity(Department, "dept", dept_header, "department_id")

        # program
        prog_header = headers.get("x-program-id") or headers.get("X-Program-ID")
        context.program = await resolve_entity(Program, "prog", prog_header, "program_id")

        # branch
        branch_header = headers.get("x-branch-id") or headers.get("X-Branch-ID")
        context.branch = await resolve_entity(Branch, "branch", branch_header, "branch_id")

        # section
        sect_header = headers.get("x-section-id") or headers.get("X-Section-ID")
        context.section = await resolve_entity(Section, "sect", sect_header, "section_id")

        # course
        course_header = headers.get("x-course-id") or headers.get("X-Course-ID")
        context.course = await resolve_entity(Course, "course", course_header, "course_id")

        latency_ms = (time.time() - start_time) * 1000.0
        from app.academic.metrics import AcademicMetricsService
        AcademicMetricsService.record_resolution(latency_ms)

        return context
