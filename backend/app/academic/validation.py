from typing import Optional
from beanie import PydanticObjectId

from app.models.org_engine.academic import AcademicYear, Semester, Department, Branch, Section
from app.models.org_engine.curriculum import Program, Course
from app.academic.exceptions import AcademicHierarchyViolation

class AcademicValidationPipeline:
    """
    Unified validation pipeline verifying collegiate hierarchy constraints
    and strict multi-tenant organization isolation.
    """
    @staticmethod
    async def validate_academic_hierarchy(
        org_id: PydanticObjectId,
        department_id: Optional[PydanticObjectId] = None,
        program_id: Optional[PydanticObjectId] = None,
        branch_id: Optional[PydanticObjectId] = None,
        semester_id: Optional[PydanticObjectId] = None,
        section_id: Optional[PydanticObjectId] = None,
        course_id: Optional[PydanticObjectId] = None
    ) -> bool:
        from app.academic.metrics import AcademicMetricsService
        
        def _fail(msg: str):
            AcademicMetricsService.record_violation()
            raise AcademicHierarchyViolation(msg)
            
        # 1. Resolve Department
        dept = None
        if department_id:
            dept = await Department.find_one(Department.id == department_id, Department.is_deleted == False)
            if not dept:
                _fail("Department not found.")
            if dept.organization_id != org_id:
                _fail("Department does not belong to this organization.")

        # 2. Resolve Program
        prog = None
        if program_id:
            prog = await Program.find_one(Program.id == program_id, Program.is_deleted == False)
            if not prog:
                _fail("Program not found.")
            if prog.organization_id != org_id:
                _fail("Program does not belong to this organization.")
            if dept and prog.department_id != dept.id:
                _fail("Program does not belong to the specified Department.")

        # 3. Resolve Branch
        branch = None
        if branch_id:
            branch = await Branch.find_one(Branch.id == branch_id, Branch.is_deleted == False)
            if not branch:
                _fail("Branch not found.")
            if branch.organization_id != org_id:
                _fail("Branch does not belong to this organization.")
            if dept and branch.department_id != dept.id:
                _fail("Branch does not belong to the specified Department.")

        # 4. Resolve Semester
        sem = None
        if semester_id:
            sem = await Semester.find_one(Semester.id == semester_id, Semester.is_deleted == False)
            if not sem:
                _fail("Semester not found.")
            if sem.organization_id != org_id:
                _fail("Semester does not belong to this organization.")

        # 5. Resolve Section
        if section_id:
            sec = await Section.find_one(Section.id == section_id, Section.is_deleted == False)
            if not sec:
                _fail("Section not found.")
            if sec.organization_id != org_id:
                _fail("Section does not belong to this organization.")
            if branch_id and sec.branch_id != branch_id:
                _fail("Section branch mismatch.")
            if semester_id and sec.semester_id != semester_id:
                _fail("Section semester mismatch.")

        # 6. Resolve Course
        if course_id:
            crs = await Course.find_one(Course.id == course_id, Course.is_deleted == False)
            if not crs:
                _fail("Course not found.")
            if crs.organization_id != org_id:
                _fail("Course does not belong to this organization.")
            if program_id and crs.program_id != program_id:
                _fail("Course program mismatch.")

        return True
