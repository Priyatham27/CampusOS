# DEPRECATED — This module is superseded by app.academic.service
# It is kept here ONLY for backward compatibility with existing tests.
# All new code MUST import from app.academic.service instead.
# This file will be removed in a future cleanup pass.
from typing import List, Optional, Tuple, Dict, Any
from beanie import PydanticObjectId
from pymongo.errors import PyMongoError
import logging

from app.core.database import get_db
from app.core.logger import logger
from app.core.exceptions import (
    OrganizationNotFound,
    DepartmentNotFound,
    ProgramNotFound,
    BranchNotFound,
    SemesterNotFound,
    SectionNotFound,
    CourseNotFound,
    DuplicateDepartment,
    DuplicateCourse,
    DuplicateSemester,
    HierarchyViolation
)
from app.repositories.organization import OrganizationRepository
from app.repositories.academic import (
    AcademicYearRepository,
    DepartmentRepository,
    ProgramRepository,
    BranchRepository,
    SemesterRepository,
    SectionRepository,
    CourseRepository
)
from app.models.org_engine.academic import AcademicYear, Semester, Department, Branch, Section
from app.models.org_engine.curriculum import Program, Course

def _generate_keywords(name: str, code: Optional[str] = None) -> Tuple[str, List[str]]:
    normalized = name.lower()
    keywords = [normalized] + [w.lower() for w in name.split()]
    if code:
        keywords.append(code.lower())
    return normalized, list(set(keywords))


class AcademicService:
    def __init__(self):
        self.org_repo = OrganizationRepository()
        self.acy_repo = AcademicYearRepository()
        self.dep_repo = DepartmentRepository()
        self.prg_repo = ProgramRepository()
        self.brn_repo = BranchRepository()
        self.sem_repo = SemesterRepository()
        self.sec_repo = SectionRepository()
        self.crs_repo = CourseRepository()

    async def _resolve_org(self, organization_id_str: str) -> Any:
        org = await self.org_repo.find_by_id(organization_id_str)
        if not org:
            raise OrganizationNotFound(f"Organization '{organization_id_str}' not found.")
        return org

    async def _run_transactional(self, func, *args, **kwargs):
        db = get_db()
        client = db.client
        try:
            async with await client.start_session() as session:
                async with session.start_transaction():
                    return await func(session, *args, **kwargs)
        except (PyMongoError, Exception) as e:
            if "replica set" in str(e).lower() or "transaction numbers" in str(e).lower():
                logger.warning("Transactions not supported. Falling back to non-transactional execution.")
                return await func(None, *args, **kwargs)
            else:
                logger.error(f"Academic transaction failure: {e}")
                raise e

    # ==========================================
    # ACADEMIC YEARS
    # ==========================================

    async def create_academic_year(self, org_id_str: str, data: dict) -> AcademicYear:
        org = await self._resolve_org(org_id_str)
        
        # Check duplicate name
        if await self.acy_repo.exists(org.id, data["name"]):
            raise HierarchyViolation(f"Academic Year name '{data['name']}' already exists.")

        count = await self.acy_repo.count(org.id)
        acy_id = f"ACY_{count + 1:06d}"
        
        normalized, keywords = _generate_keywords(data["name"])
        acy = AcademicYear(
            academicYearId=acy_id,
            organizationId=org.id,
            name=data["name"],
            startDate=data["startDate"],
            endDate=data["endDate"],
            current=data.get("current", False),
            normalizedName=normalized,
            searchKeywords=keywords
        )

        async def _save(session):
            if acy.current:
                # Set others to current=False
                await AcademicYear.find(
                    AcademicYear.organization_id == org.id,
                    AcademicYear.is_deleted == False,
                    session=session
                ).update({"$set": {"current": False}}, session=session)
            return await self.acy_repo.create(acy, session=session)

        res = await self._run_transactional(_save)
        logger.info(f"Academic Year '{res.name}' (ID: {res.academic_year_id}) created.")
        return res

    async def get_academic_year(self, org_id_str: str, acy_id: str) -> AcademicYear:
        org = await self._resolve_org(org_id_str)
        acy = await self.acy_repo.find_by_id(acy_id, org.id)
        if not acy:
            raise HierarchyViolation("Academic Year not found.")
        return acy

    async def list_academic_years(self, org_id_str: str, skip: int = 0, limit: int = 10, sort_by: str = "createdAt", sort_order: str = "asc", filters: Optional[dict] = None) -> Tuple[List[AcademicYear], int]:
        org = await self._resolve_org(org_id_str)
        items = await self.acy_repo.list(org.id, skip, limit, sort_by, sort_order, filters)
        total = await self.acy_repo.count(org.id, filters)
        return items, total

    async def update_academic_year(self, org_id_str: str, acy_id: str, update_data: dict) -> AcademicYear:
        org = await self._resolve_org(org_id_str)
        acy = await self.acy_repo.find_by_id(acy_id, org.id)
        if not acy:
            raise HierarchyViolation("Academic Year not found.")

        if "name" in update_data and update_data["name"] != acy.name:
            if await self.acy_repo.exists(org.id, update_data["name"]):
                raise HierarchyViolation(f"Academic Year name '{update_data['name']}' already exists.")
            normalized, keywords = _generate_keywords(update_data["name"])
            update_data["normalizedName"] = normalized
            update_data["searchKeywords"] = keywords

        async def _update(session):
            if update_data.get("current"):
                await AcademicYear.find(
                    AcademicYear.organization_id == org.id,
                    AcademicYear.is_deleted == False,
                    session=session
                ).update({"$set": {"current": False}}, session=session)
            return await self.acy_repo.update(acy, update_data, session=session)

        res = await self._run_transactional(_update)
        logger.info(f"Academic Year ID: {acy_id} updated.")
        return res

    async def delete_academic_year(self, org_id_str: str, acy_id: str) -> bool:
        org = await self._resolve_org(org_id_str)
        acy = await self.acy_repo.find_by_id(acy_id, org.id)
        if not acy:
            raise HierarchyViolation("Academic Year not found.")
        await self.acy_repo.delete(acy)
        logger.info(f"Academic Year ID: {acy_id} soft deleted.")
        return True

    # ==========================================
    # DEPARTMENTS
    # ==========================================

    async def create_department(self, org_id_str: str, data: dict) -> Department:
        org = await self._resolve_org(org_id_str)
        code_upper = data["code"].upper()
        if await self.dep_repo.exists(org.id, code_upper):
            raise DuplicateDepartment(f"Department code '{code_upper}' already registered in this organization.")

        count = await self.dep_repo.count(org.id)
        dep_id = f"DEP_{count + 1:06d}"

        normalized, keywords = _generate_keywords(data["name"], code_upper)
        dep = Department(
            departmentId=dep_id,
            organizationId=org.id,
            name=data["name"],
            code=code_upper,
            hod=data.get("hod"),
            description=data.get("description"),
            status=data.get("status", "ACTIVE"),
            normalizedName=normalized,
            searchKeywords=keywords
        )
        res = await self.dep_repo.create(dep)
        logger.info(f"Department '{res.name}' (ID: {res.department_id}) created.")
        return res

    async def get_department(self, org_id_str: str, dep_id: str) -> Department:
        org = await self._resolve_org(org_id_str)
        dep = await self.dep_repo.find_by_id(dep_id, org.id)
        if not dep:
            raise DepartmentNotFound(f"Department ID '{dep_id}' not found.")
        return dep

    async def list_departments(self, org_id_str: str, skip: int = 0, limit: int = 10, sort_by: str = "createdAt", sort_order: str = "asc", filters: Optional[dict] = None) -> Tuple[List[Department], int]:
        org = await self._resolve_org(org_id_str)
        items = await self.dep_repo.list(org.id, skip, limit, sort_by, sort_order, filters)
        total = await self.dep_repo.count(org.id, filters)
        return items, total

    async def update_department(self, org_id_str: str, dep_id: str, update_data: dict) -> Department:
        org = await self._resolve_org(org_id_str)
        dep = await self.dep_repo.find_by_id(dep_id, org.id)
        if not dep:
            raise DepartmentNotFound(f"Department ID '{dep_id}' not found.")

        if "code" in update_data:
            code_upper = update_data["code"].upper()
            if code_upper != dep.code and await self.dep_repo.exists(org.id, code_upper):
                raise DuplicateDepartment(f"Department code '{code_upper}' already registered.")
            update_data["code"] = code_upper

        if "name" in update_data or "code" in update_data:
            name = update_data.get("name", dep.name)
            code = update_data.get("code", dep.code)
            normalized, keywords = _generate_keywords(name, code)
            update_data["normalizedName"] = normalized
            update_data["searchKeywords"] = keywords

        res = await self.dep_repo.update(dep, update_data)
        logger.info(f"Department ID: {dep_id} updated.")
        return res

    async def delete_department(self, org_id_str: str, dep_id: str) -> bool:
        org = await self._resolve_org(org_id_str)
        dep = await self.dep_repo.find_by_id(dep_id, org.id)
        if not dep:
            raise DepartmentNotFound(f"Department ID '{dep_id}' not found.")
        await self.dep_repo.delete(dep)
        logger.info(f"Department ID: {dep_id} soft deleted.")
        return True

    # ==========================================
    # PROGRAMS
    # ==========================================

    async def create_program(self, org_id_str: str, data: dict) -> Program:
        org = await self._resolve_org(org_id_str)
        
        # Validate Department reference
        dep = await Department.find_one(
            Department.id == PydanticObjectId(data["departmentId"]),
            Department.organization_id == org.id,
            Department.is_deleted == False
        )
        if not dep:
            raise DepartmentNotFound("Referenced Department does not exist.")

        # Check unique program name inside department/organization
        if await self.prg_repo.exists(org.id, dep.id, data["name"]):
            raise HierarchyViolation(f"Program with name '{data['name']}' already exists in this Department.")

        count = await self.prg_repo.count(org.id)
        prg_id = f"PRG_{count + 1:06d}"

        normalized, keywords = _generate_keywords(data["name"])
        prg = Program(
            programId=prg_id,
            organizationId=org.id,
            departmentId=dep.id,
            name=data["name"],
            duration=data["duration"],
            level=data.get("level", "UNDERGRADUATE"),
            normalizedName=normalized,
            searchKeywords=keywords
        )
        res = await self.prg_repo.create(prg)
        logger.info(f"Program '{res.name}' (ID: {res.program_id}) created.")
        return res

    async def get_program(self, org_id_str: str, prg_id: str) -> Program:
        org = await self._resolve_org(org_id_str)
        prg = await self.prg_repo.find_by_id(prg_id, org.id)
        if not prg:
            raise ProgramNotFound(f"Program ID '{prg_id}' not found.")
        return prg

    async def list_programs(self, org_id_str: str, skip: int = 0, limit: int = 10, sort_by: str = "createdAt", sort_order: str = "asc", filters: Optional[dict] = None) -> Tuple[List[Program], int]:
        org = await self._resolve_org(org_id_str)
        items = await self.prg_repo.list(org.id, skip, limit, sort_by, sort_order, filters)
        total = await self.prg_repo.count(org.id, filters)
        return items, total

    async def update_program(self, org_id_str: str, prg_id: str, update_data: dict) -> Program:
        org = await self._resolve_org(org_id_str)
        prg = await self.prg_repo.find_by_id(prg_id, org.id)
        if not prg:
            raise ProgramNotFound(f"Program ID '{prg_id}' not found.")

        dep_id = prg.department_id
        if "departmentId" in update_data:
            dep_obj_id = PydanticObjectId(update_data["departmentId"])
            dep = await Department.find_one(
                Department.id == dep_obj_id,
                Department.organization_id == org.id,
                Department.is_deleted == False
            )
            if not dep:
                raise DepartmentNotFound("Referenced Department does not exist.")
            dep_id = dep.id
            update_data["departmentId"] = dep_id

        if "name" in update_data:
            name = update_data["name"]
            if name != prg.name and await self.prg_repo.exists(org.id, dep_id, name):
                raise HierarchyViolation(f"Program with name '{name}' already exists in this Department.")
            normalized, keywords = _generate_keywords(name)
            update_data["normalizedName"] = normalized
            update_data["searchKeywords"] = keywords

        res = await self.prg_repo.update(prg, update_data)
        logger.info(f"Program ID: {prg_id} updated.")
        return res

    async def delete_program(self, org_id_str: str, prg_id: str) -> bool:
        org = await self._resolve_org(org_id_str)
        prg = await self.prg_repo.find_by_id(prg_id, org.id)
        if not prg:
            raise ProgramNotFound(f"Program ID '{prg_id}' not found.")
        await self.prg_repo.delete(prg)
        logger.info(f"Program ID: {prg_id} soft deleted.")
        return True

    # ==========================================
    # BRANCHES
    # ==========================================

    async def create_branch(self, org_id_str: str, data: dict) -> Branch:
        org = await self._resolve_org(org_id_str)

        # Validate Department reference
        dep = await Department.find_one(
            Department.id == PydanticObjectId(data["departmentId"]),
            Department.organization_id == org.id,
            Department.is_deleted == False
        )
        if not dep:
            raise DepartmentNotFound("Referenced Department does not exist.")

        code_upper = data["code"].upper()
        if await self.brn_repo.exists(dep.id, code_upper):
            raise HierarchyViolation(f"Branch code '{code_upper}' already exists in this Department.")

        count = await self.brn_repo.count(org.id)
        brn_id = f"BRN_{count + 1:06d}"

        normalized, keywords = _generate_keywords(data["name"], code_upper)
        brn = Branch(
            branchId=brn_id,
            organizationId=org.id,
            departmentId=dep.id,
            code=code_upper,
            name=data["name"],
            normalizedName=normalized,
            searchKeywords=keywords
        )
        res = await self.brn_repo.create(brn)
        logger.info(f"Branch '{res.name}' (ID: {res.branch_id}) created.")
        return res

    async def get_branch(self, org_id_str: str, brn_id: str) -> Branch:
        org = await self._resolve_org(org_id_str)
        brn = await self.brn_repo.find_by_id(brn_id, org.id)
        if not brn:
            raise BranchNotFound(f"Branch ID '{brn_id}' not found.")
        return brn

    async def list_branches(self, org_id_str: str, skip: int = 0, limit: int = 10, sort_by: str = "createdAt", sort_order: str = "asc", filters: Optional[dict] = None) -> Tuple[List[Branch], int]:
        org = await self._resolve_org(org_id_str)
        items = await self.brn_repo.list(org.id, skip, limit, sort_by, sort_order, filters)
        total = await self.brn_repo.count(org.id, filters)
        return items, total

    async def update_branch(self, org_id_str: str, brn_id: str, update_data: dict) -> Branch:
        org = await self._resolve_org(org_id_str)
        brn = await self.brn_repo.find_by_id(brn_id, org.id)
        if not brn:
            raise BranchNotFound(f"Branch ID '{brn_id}' not found.")

        dep_id = brn.department_id
        if "departmentId" in update_data:
            dep_obj_id = PydanticObjectId(update_data["departmentId"])
            dep = await Department.find_one(
                Department.id == dep_obj_id,
                Department.organization_id == org.id,
                Department.is_deleted == False
            )
            if not dep:
                raise DepartmentNotFound("Referenced Department does not exist.")
            dep_id = dep.id
            update_data["departmentId"] = dep_id

        if "code" in update_data:
            code_upper = update_data["code"].upper()
            if code_upper != brn.code and await self.brn_repo.exists(dep_id, code_upper):
                raise HierarchyViolation(f"Branch code '{code_upper}' already exists in the target Department.")
            update_data["code"] = code_upper

        if "name" in update_data or "code" in update_data:
            name = update_data.get("name", brn.name)
            code = update_data.get("code", brn.code)
            normalized, keywords = _generate_keywords(name, code)
            update_data["normalizedName"] = normalized
            update_data["searchKeywords"] = keywords

        res = await self.brn_repo.update(brn, update_data)
        logger.info(f"Branch ID: {brn_id} updated.")
        return res

    async def delete_branch(self, org_id_str: str, brn_id: str) -> bool:
        org = await self._resolve_org(org_id_str)
        brn = await self.brn_repo.find_by_id(brn_id, org.id)
        if not brn:
            raise BranchNotFound(f"Branch ID '{brn_id}' not found.")
        await self.brn_repo.delete(brn)
        logger.info(f"Branch ID: {brn_id} soft deleted.")
        return True

    # ==========================================
    # SEMESTERS
    # ==========================================

    async def create_semester(self, org_id_str: str, data: dict) -> Semester:
        org = await self._resolve_org(org_id_str)
        semester_number = data["number"]

        # Validate sequence: semesters must be sequential starting at 1
        highest_sem = await Semester.find(
            Semester.organization_id == org.id,
            Semester.is_deleted == False
        ).sort("-number").limit(1).first_or_none()
        max_sem = highest_sem.number if highest_sem else 0

        if semester_number != max_sem + 1:
            raise HierarchyViolation(f"Semester numbers must be sequential. Next expected semester: {max_sem + 1}")

        if await self.sem_repo.exists(org.id, semester_number):
            raise DuplicateSemester(f"Semester number {semester_number} already registered in this organization.")

        count = await self.sem_repo.count(org.id)
        sem_id = f"SEM_{count + 1:06d}"

        normalized, keywords = _generate_keywords(data["name"])
        sem = Semester(
            semesterId=sem_id,
            organizationId=org.id,
            number=semester_number,
            name=data["name"],
            status=data.get("status", "ACTIVE"),
            normalizedName=normalized,
            searchKeywords=keywords
        )
        res = await self.sem_repo.create(sem)
        logger.info(f"Semester '{res.name}' (ID: {res.semester_id}) created.")
        return res

    async def get_semester(self, org_id_str: str, sem_id: str) -> Semester:
        org = await self._resolve_org(org_id_str)
        sem = await self.sem_repo.find_by_id(sem_id, org.id)
        if not sem:
            raise SemesterNotFound(f"Semester ID '{sem_id}' not found.")
        return sem

    async def list_semesters(self, org_id_str: str, skip: int = 0, limit: int = 10, sort_by: str = "number", sort_order: str = "asc", filters: Optional[dict] = None) -> Tuple[List[Semester], int]:
        org = await self._resolve_org(org_id_str)
        items = await self.sem_repo.list(org.id, skip, limit, sort_by, sort_order, filters)
        total = await self.sem_repo.count(org.id, filters)
        return items, total

    async def update_semester(self, org_id_str: str, sem_id: str, update_data: dict) -> Semester:
        org = await self._resolve_org(org_id_str)
        sem = await self.sem_repo.find_by_id(sem_id, org.id)
        if not sem:
            raise SemesterNotFound(f"Semester ID '{sem_id}' not found.")

        # Semester sequential rules restrict modifying semester numbers arbitrarily
        if "number" in update_data:
            number = update_data["number"]
            if number != sem.number:
                raise HierarchyViolation("Modifying sequential semester numbers directly is restricted.")

        if "name" in update_data:
            normalized, keywords = _generate_keywords(update_data["name"])
            update_data["normalizedName"] = normalized
            update_data["searchKeywords"] = keywords

        res = await self.sem_repo.update(sem, update_data)
        logger.info(f"Semester ID: {sem_id} updated.")
        return res

    async def delete_semester(self, org_id_str: str, sem_id: str) -> bool:
        org = await self._resolve_org(org_id_str)
        sem = await self.sem_repo.find_by_id(sem_id, org.id)
        if not sem:
            raise SemesterNotFound(f"Semester ID '{sem_id}' not found.")
        
        # Soft delete is only permitted on the highest semester number to keep sequence sequential
        highest_sem = await Semester.find(
            Semester.organization_id == org.id,
            Semester.is_deleted == False
        ).sort("-number").limit(1).first_or_none()
        max_sem = highest_sem.number if highest_sem else 0

        
        if sem.number < max_sem:
            raise HierarchyViolation(f"Cannot delete semester {sem.number} as it would break the sequential integrity. Only the highest semester ({max_sem}) can be removed.")

        await self.sem_repo.delete(sem)
        logger.info(f"Semester ID: {sem_id} soft deleted.")
        return True

    # ==========================================
    # SECTIONS
    # ==========================================

    async def create_section(self, org_id_str: str, data: dict) -> Section:
        org = await self._resolve_org(org_id_str)

        # Validate Branch
        brn = await Branch.find_one(
            Branch.id == PydanticObjectId(data["branchId"]),
            Branch.organization_id == org.id,
            Branch.is_deleted == False
        )
        if not brn:
            raise BranchNotFound("Referenced Branch does not exist.")

        # Validate Semester
        sem = await Semester.find_one(
            Semester.id == PydanticObjectId(data["semesterId"]),
            Semester.organization_id == org.id,
            Semester.is_deleted == False
        )
        if not sem:
            raise SemesterNotFound("Referenced Semester does not exist.")

        # Check uniqueness inside branch and semester
        if await self.sec_repo.exists(brn.id, sem.id, data["name"]):
            raise HierarchyViolation(f"Section '{data['name']}' already exists for this branch in this semester.")

        count = await self.sec_repo.count(org.id)
        sec_id = f"SEC_{count + 1:06d}"

        normalized, keywords = _generate_keywords(data["name"])
        sec = Section(
            sectionId=sec_id,
            organizationId=org.id,
            branchId=brn.id,
            semesterId=sem.id,
            name=data["name"],
            strength=data["strength"],
            normalizedName=normalized,
            searchKeywords=keywords
        )
        res = await self.sec_repo.create(sec)
        logger.info(f"Section '{res.name}' (ID: {res.section_id}) created.")
        return res

    async def get_section(self, org_id_str: str, sec_id: str) -> Section:
        org = await self._resolve_org(org_id_str)
        sec = await self.sec_repo.find_by_id(sec_id, org.id)
        if not sec:
            raise SectionNotFound(f"Section ID '{sec_id}' not found.")
        return sec

    async def list_sections(self, org_id_str: str, skip: int = 0, limit: int = 10, sort_by: str = "createdAt", sort_order: str = "asc", filters: Optional[dict] = None) -> Tuple[List[Section], int]:
        org = await self._resolve_org(org_id_str)
        items = await self.sec_repo.list(org.id, skip, limit, sort_by, sort_order, filters)
        total = await self.sec_repo.count(org.id, filters)
        return items, total

    async def update_section(self, org_id_str: str, sec_id: str, update_data: dict) -> Section:
        org = await self._resolve_org(org_id_str)
        sec = await self.sec_repo.find_by_id(sec_id, org.id)
        if not sec:
            raise SectionNotFound(f"Section ID '{sec_id}' not found.")

        brn_id = sec.branch_id
        if "branchId" in update_data:
            brn_obj_id = PydanticObjectId(update_data["branchId"])
            brn = await Branch.find_one(
                Branch.id == brn_obj_id,
                Branch.organization_id == org.id,
                Branch.is_deleted == False
            )
            if not brn:
                raise BranchNotFound("Referenced Branch does not exist.")
            brn_id = brn.id
            update_data["branchId"] = brn_id

        sem_id = sec.semester_id
        if "semesterId" in update_data:
            sem_obj_id = PydanticObjectId(update_data["semesterId"])
            sem = await Semester.find_one(
                Semester.id == sem_obj_id,
                Semester.organization_id == org.id,
                Semester.is_deleted == False
            )
            if not sem:
                raise SemesterNotFound("Referenced Semester does not exist.")
            sem_id = sem.id
            update_data["semesterId"] = sem_id

        if "name" in update_data:
            name = update_data["name"]
            if name != sec.name and await self.sec_repo.exists(brn_id, sem_id, name):
                raise HierarchyViolation(f"Section '{name}' already exists in target Branch/Semester.")
            normalized, keywords = _generate_keywords(name)
            update_data["normalizedName"] = normalized
            update_data["searchKeywords"] = keywords

        res = await self.sec_repo.update(sec, update_data)
        logger.info(f"Section ID: {sec_id} updated.")
        return res

    async def delete_section(self, org_id_str: str, sec_id: str) -> bool:
        org = await self._resolve_org(org_id_str)
        sec = await self.sec_repo.find_by_id(sec_id, org.id)
        if not sec:
            raise SectionNotFound(f"Section ID '{sec_id}' not found.")
        await self.sec_repo.delete(sec)
        logger.info(f"Section ID: {sec_id} soft deleted.")
        return True

    # ==========================================
    # COURSES
    # ==========================================

    async def create_course(self, org_id_str: str, data: dict) -> Course:
        org = await self._resolve_org(org_id_str)

        # Validate Program
        prg = await Program.find_one(
            Program.id == PydanticObjectId(data["programId"]),
            Program.organization_id == org.id,
            Program.is_deleted == False
        )
        if not prg:
            raise ProgramNotFound("Referenced Program does not exist.")

        code_upper = data["courseCode"].upper()
        if await self.crs_repo.exists(org.id, code_upper):
            raise DuplicateCourse(f"Course code '{code_upper}' already registered inside this organization.")

        count = await self.crs_repo.count(org.id)
        crs_id = f"COURSE_{count + 1:06d}"

        normalized, keywords = _generate_keywords(data["courseCode"]) # Course code is also name/keywords base
        crs = Course(
            courseId=crs_id,
            organizationId=org.id,
            programId=prg.id,
            courseCode=code_upper,
            credits=data["credits"],
            semester=data["semester"],
            normalizedName=normalized,
            searchKeywords=keywords
        )
        res = await self.crs_repo.create(crs)
        logger.info(f"Course '{res.course_code}' (ID: {res.course_id}) created.")
        return res

    async def get_course(self, org_id_str: str, crs_id: str) -> Course:
        org = await self._resolve_org(org_id_str)
        crs = await self.crs_repo.find_by_id(crs_id, org.id)
        if not crs:
            raise CourseNotFound(f"Course ID '{crs_id}' not found.")
        return crs

    async def list_courses(self, org_id_str: str, skip: int = 0, limit: int = 10, sort_by: str = "createdAt", sort_order: str = "asc", filters: Optional[dict] = None) -> Tuple[List[Course], int]:
        org = await self._resolve_org(org_id_str)
        items = await self.crs_repo.list(org.id, skip, limit, sort_by, sort_order, filters)
        total = await self.crs_repo.count(org.id, filters)
        return items, total

    async def update_course(self, org_id_str: str, crs_id: str, update_data: dict) -> Course:
        org = await self._resolve_org(org_id_str)
        crs = await self.crs_repo.find_by_id(crs_id, org.id)
        if not crs:
            raise CourseNotFound(f"Course ID '{crs_id}' not found.")

        if "programId" in update_data:
            prg_obj_id = PydanticObjectId(update_data["programId"])
            prg = await Program.find_one(
                Program.id == prg_obj_id,
                Program.organization_id == org.id,
                Program.is_deleted == False
            )
            if not prg:
                raise ProgramNotFound("Referenced Program does not exist.")
            update_data["programId"] = prg.id

        if "courseCode" in update_data:
            code_upper = update_data["courseCode"].upper()
            if code_upper != crs.course_code and await self.crs_repo.exists(org.id, code_upper):
                raise DuplicateCourse(f"Course code '{code_upper}' already registered.")
            update_data["courseCode"] = code_upper
            normalized, keywords = _generate_keywords(code_upper)
            update_data["normalizedName"] = normalized
            update_data["searchKeywords"] = keywords

        res = await self.crs_repo.update(crs, update_data)
        logger.info(f"Course ID: {crs_id} updated.")
        return res

    async def delete_course(self, org_id_str: str, crs_id: str) -> bool:
        org = await self._resolve_org(org_id_str)
        crs = await self.crs_repo.find_by_id(crs_id, org.id)
        if not crs:
            raise CourseNotFound(f"Course ID '{crs_id}' not found.")
        await self.crs_repo.delete(crs)
        logger.info(f"Course ID: {crs_id} soft deleted.")
        return True

    # ==========================================
    # BULK OPERATIONS & TRANSACTIONS
    # ==========================================

    async def bulk_create_academic_years(self, org_id_str: str, items_data: List[dict]) -> List[AcademicYear]:
        org = await self._resolve_org(org_id_str)
        
        async def _bulk_save(session):
            inserted = []
            count = await self.acy_repo.count(org.id, session=session)
            
            # Local set to validate batch duplicates
            batch_names = set()
            
            for idx, item in enumerate(items_data):
                name = item["name"]
                if name in batch_names:
                    raise HierarchyViolation(f"Duplicate name '{name}' found in bulk upload batch.")
                batch_names.add(name)

                if await self.acy_repo.exists(org.id, name, session=session):
                    raise HierarchyViolation(f"Academic Year name '{name}' already exists.")

                acy_id = f"ACY_{count + idx + 1:06d}"
                normalized, keywords = _generate_keywords(name)
                
                acy = AcademicYear(
                    academicYearId=acy_id,
                    organizationId=org.id,
                    name=name,
                    startDate=item["startDate"],
                    endDate=item["endDate"],
                    current=item.get("current", False),
                    normalizedName=normalized,
                    searchKeywords=keywords
                )
                if acy.current:
                    await AcademicYear.find(
                        AcademicYear.organization_id == org.id,
                        AcademicYear.is_deleted == False,
                        session=session
                    ).update({"$set": {"current": False}}, session=session)
                
                res = await self.acy_repo.create(acy, session=session)
                inserted.append(res)
            return inserted

        return await self._run_transactional(_bulk_save)

    async def bulk_create_departments(self, org_id_str: str, items_data: List[dict]) -> List[Department]:
        org = await self._resolve_org(org_id_str)
        
        async def _bulk_save(session):
            inserted = []
            count = await self.dep_repo.count(org.id, session=session)
            batch_codes = set()
            
            for idx, item in enumerate(items_data):
                code = item["code"].upper()
                if code in batch_codes:
                    raise DuplicateDepartment(f"Duplicate department code '{code}' in bulk batch.")
                batch_codes.add(code)

                if await self.dep_repo.exists(org.id, code, session=session):
                    raise DuplicateDepartment(f"Department code '{code}' already registered.")

                dep_id = f"DEP_{count + idx + 1:06d}"
                normalized, keywords = _generate_keywords(item["name"], code)
                
                dep = Department(
                    departmentId=dep_id,
                    organizationId=org.id,
                    name=item["name"],
                    code=code,
                    hod=item.get("hod"),
                    description=item.get("description"),
                    status=item.get("status", "ACTIVE"),
                    normalizedName=normalized,
                    searchKeywords=keywords
                )
                res = await self.dep_repo.create(dep, session=session)
                inserted.append(res)
            return inserted

        return await self._run_transactional(_bulk_save)

    async def bulk_create_programs(self, org_id_str: str, items_data: List[dict]) -> List[Program]:
        org = await self._resolve_org(org_id_str)

        async def _bulk_save(session):
            inserted = []
            count = await self.prg_repo.count(org.id, session=session)
            
            for idx, item in enumerate(items_data):
                dep_obj_id = PydanticObjectId(item["departmentId"])
                dep = await Department.find_one(
                    Department.id == dep_obj_id,
                    Department.organization_id == org.id,
                    Department.is_deleted == False,
                    session=session
                )
                if not dep:
                    raise DepartmentNotFound("Referenced Department does not exist.")

                if await self.prg_repo.exists(org.id, dep.id, item["name"], session=session):
                    raise HierarchyViolation(f"Program with name '{item['name']}' already exists.")

                prg_id = f"PRG_{count + idx + 1:06d}"
                normalized, keywords = _generate_keywords(item["name"])

                prg = Program(
                    programId=prg_id,
                    organizationId=org.id,
                    departmentId=dep.id,
                    name=item["name"],
                    duration=item["duration"],
                    level=item.get("level", "UNDERGRADUATE"),
                    normalizedName=normalized,
                    searchKeywords=keywords
                )
                res = await self.prg_repo.create(prg, session=session)
                inserted.append(res)
            return inserted

        return await self._run_transactional(_bulk_save)

    async def bulk_create_branches(self, org_id_str: str, items_data: List[dict]) -> List[Branch]:
        org = await self._resolve_org(org_id_str)

        async def _bulk_save(session):
            inserted = []
            count = await self.brn_repo.count(org.id, session=session)

            for idx, item in enumerate(items_data):
                dep_obj_id = PydanticObjectId(item["departmentId"])
                dep = await Department.find_one(
                    Department.id == dep_obj_id,
                    Department.organization_id == org.id,
                    Department.is_deleted == False,
                    session=session
                )
                if not dep:
                    raise DepartmentNotFound("Referenced Department does not exist.")

                code_upper = item["code"].upper()
                if await self.brn_repo.exists(dep.id, code_upper, session=session):
                    raise HierarchyViolation(f"Branch code '{code_upper}' already registered in target Department.")

                brn_id = f"BRN_{count + idx + 1:06d}"
                normalized, keywords = _generate_keywords(item["name"], code_upper)

                brn = Branch(
                    branchId=brn_id,
                    organizationId=org.id,
                    departmentId=dep.id,
                    code=code_upper,
                    name=item["name"],
                    normalizedName=normalized,
                    searchKeywords=keywords
                )
                res = await self.brn_repo.create(brn, session=session)
                inserted.append(res)
            return inserted

        return await self._run_transactional(_bulk_save)

    async def bulk_create_semesters(self, org_id_str: str, items_data: List[dict]) -> List[Semester]:
        org = await self._resolve_org(org_id_str)

        async def _bulk_save(session):
            inserted = []
            count = await self.sem_repo.count(org.id, session=session)
            
            # Bulk semesters creation must also maintain sequence rules
            # We sort items_data by semester number ascending
            sorted_items = sorted(items_data, key=lambda x: x["number"])

            for idx, item in enumerate(sorted_items):
                semester_number = item["number"]
                highest_sem = await Semester.find(
                    Semester.organization_id == org.id,
                    Semester.is_deleted == False,
                    session=session
                ).sort("-number").limit(1).first_or_none()
                max_sem = highest_sem.number if highest_sem else 0

                if semester_number != max_sem + 1:
                    raise HierarchyViolation(f"Semester numbers must be sequential. Next expected: {max_sem + 1}")

                if await self.sem_repo.exists(org.id, semester_number, session=session):
                    raise DuplicateSemester(f"Semester number {semester_number} already registered.")

                sem_id = f"SEM_{count + idx + 1:06d}"
                normalized, keywords = _generate_keywords(item["name"])

                sem = Semester(
                    semesterId=sem_id,
                    organizationId=org.id,
                    number=semester_number,
                    name=item["name"],
                    status=item.get("status", "ACTIVE"),
                    normalizedName=normalized,
                    searchKeywords=keywords
                )
                res = await self.sem_repo.create(sem, session=session)
                inserted.append(res)
            return inserted

        return await self._run_transactional(_bulk_save)

    async def bulk_create_sections(self, org_id_str: str, items_data: List[dict]) -> List[Section]:
        org = await self._resolve_org(org_id_str)

        async def _bulk_save(session):
            inserted = []
            count = await self.sec_repo.count(org.id, session=session)

            for idx, item in enumerate(items_data):
                brn_obj_id = PydanticObjectId(item["branchId"])
                brn = await Branch.find_one(
                    Branch.id == brn_obj_id,
                    Branch.organization_id == org.id,
                    Branch.is_deleted == False,
                    session=session
                )
                if not brn:
                    raise BranchNotFound("Referenced Branch does not exist.")

                sem_obj_id = PydanticObjectId(item["semesterId"])
                sem = await Semester.find_one(
                    Semester.id == sem_obj_id,
                    Semester.organization_id == org.id,
                    Semester.is_deleted == False,
                    session=session
                )
                if not sem:
                    raise SemesterNotFound("Referenced Semester does not exist.")

                if await self.sec_repo.exists(brn.id, sem.id, item["name"], session=session):
                    raise HierarchyViolation(f"Section '{item['name']}' already registered for target Branch and Semester.")

                sec_id = f"SEC_{count + idx + 1:06d}"
                normalized, keywords = _generate_keywords(item["name"])

                sec = Section(
                    sectionId=sec_id,
                    organizationId=org.id,
                    branchId=brn.id,
                    semesterId=sem.id,
                    name=item["name"],
                    strength=item["strength"],
                    normalizedName=normalized,
                    searchKeywords=keywords
                )
                res = await self.sec_repo.create(sec, session=session)
                inserted.append(res)
            return inserted

        return await self._run_transactional(_bulk_save)

    async def bulk_create_courses(self, org_id_str: str, items_data: List[dict]) -> List[Course]:
        org = await self._resolve_org(org_id_str)

        async def _bulk_save(session):
            inserted = []
            count = await self.crs_repo.count(org.id, session=session)
            batch_codes = set()

            for idx, item in enumerate(items_data):
                prg_obj_id = PydanticObjectId(item["programId"])
                prg = await Program.find_one(
                    Program.id == prg_obj_id,
                    Program.organization_id == org.id,
                    Program.is_deleted == False,
                    session=session
                )
                if not prg:
                    raise ProgramNotFound("Referenced Program does not exist.")

                code_upper = item["courseCode"].upper()
                if code_upper in batch_codes:
                    raise DuplicateCourse(f"Duplicate course code '{code_upper}' in bulk batch.")
                batch_codes.add(code_upper)

                if await self.crs_repo.exists(org.id, code_upper, session=session):
                    raise DuplicateCourse(f"Course code '{code_upper}' already registered.")

                crs_id = f"COURSE_{count + idx + 1:06d}"
                normalized, keywords = _generate_keywords(code_upper)

                crs = Course(
                    courseId=crs_id,
                    organizationId=org.id,
                    programId=prg.id,
                    courseCode=code_upper,
                    credits=item["credits"],
                    semester=item["semester"],
                    normalizedName=normalized,
                    searchKeywords=keywords
                )
                res = await self.crs_repo.create(crs, session=session)
                inserted.append(res)
            return inserted

        return await self._run_transactional(_bulk_save)

    # ==========================================
    # BULK UPDATES
    # ==========================================

    async def _bulk_update_generic(self, org_id_str: str, model_cls: Any, repo: Any, items_data: List[dict], custom_id_key: str) -> bool:
        org = await self._resolve_org(org_id_str)
        
        async def _bulk_update(session):
            for item in items_data:
                custom_id = item[custom_id_key]
                doc = await repo.find_by_id(custom_id, org.id, session=session)
                if not doc:
                    raise HierarchyViolation(f"Document with ID '{custom_id}' not found.")
                
                # Check for unique constraints if updated
                # (handled on single entity update logic inside repo, but we can do safety validations here)
                await repo.update(doc, item, session=session)
            return True

        return await self._run_transactional(_bulk_update)

    async def bulk_update_departments(self, org_id_str: str, items_data: List[dict]) -> bool:
        return await self._bulk_update_generic(org_id_str, Department, self.dep_repo, items_data, "departmentId")

    async def bulk_update_programs(self, org_id_str: str, items_data: List[dict]) -> bool:
        return await self._bulk_update_generic(org_id_str, Program, self.prg_repo, items_data, "programId")

    async def bulk_update_branches(self, org_id_str: str, items_data: List[dict]) -> bool:
        return await self._bulk_update_generic(org_id_str, Branch, self.brn_repo, items_data, "branchId")

    async def bulk_update_sections(self, org_id_str: str, items_data: List[dict]) -> bool:
        return await self._bulk_update_generic(org_id_str, Section, self.sec_repo, items_data, "sectionId")

    async def bulk_update_courses(self, org_id_str: str, items_data: List[dict]) -> bool:
        return await self._bulk_update_generic(org_id_str, Course, self.crs_repo, items_data, "courseId")

    # ==========================================
    # BULK DELETIONS (SOFT DELETE)
    # ==========================================

    async def _bulk_delete_generic(self, org_id_str: str, model_cls: Any, repo: Any, ids: List[str], custom_id_key: str) -> bool:
        org = await self._resolve_org(org_id_str)

        async def _bulk_delete(session):
            for cid in ids:
                doc = await repo.find_by_id(cid, org.id, session=session)
                if not doc:
                    raise HierarchyViolation(f"Document with ID '{cid}' not found.")
                await repo.delete(doc, session=session)
            return True

        return await self._run_transactional(_bulk_delete)

    async def bulk_delete_departments(self, org_id_str: str, ids: List[str]) -> bool:
        return await self._bulk_delete_generic(org_id_str, Department, self.dep_repo, ids, "departmentId")

    async def bulk_delete_programs(self, org_id_str: str, ids: List[str]) -> bool:
        return await self._bulk_delete_generic(org_id_str, Program, self.prg_repo, ids, "programId")

    async def bulk_delete_branches(self, org_id_str: str, ids: List[str]) -> bool:
        return await self._bulk_delete_generic(org_id_str, Branch, self.brn_repo, ids, "branchId")

    async def bulk_delete_sections(self, org_id_str: str, ids: List[str]) -> bool:
        return await self._bulk_delete_generic(org_id_str, Section, self.sec_repo, ids, "sectionId")

    async def bulk_delete_courses(self, org_id_str: str, ids: List[str]) -> bool:
        return await self._bulk_delete_generic(org_id_str, Course, self.crs_repo, ids, "courseId")
