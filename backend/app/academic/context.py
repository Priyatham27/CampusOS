from typing import Optional
from pydantic import BaseModel
from contextvars import ContextVar

from app.models.org_engine.academic import AcademicYear, Semester, Department, Branch, Section
from app.models.org_engine.curriculum import Program, Course
from app.models.calendar import AcademicCalendar

class AcademicContext(BaseModel):
    academic_year: Optional[AcademicYear] = None
    semester: Optional[Semester] = None
    department: Optional[Department] = None
    program: Optional[Program] = None
    branch: Optional[Branch] = None
    section: Optional[Section] = None
    course: Optional[Course] = None
    active_calendar: Optional[AcademicCalendar] = None

    class Config:
        arbitrary_types_allowed = True

_academic_context_var: ContextVar[AcademicContext] = ContextVar(
    "academic_context", default=AcademicContext()
)

def get_academic_context() -> AcademicContext:
    return _academic_context_var.get()

def set_academic_context(context: AcademicContext):
    return _academic_context_var.set(context)

def reset_academic_context(token):
    _academic_context_var.reset(token)
