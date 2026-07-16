from typing import List, Optional, Tuple, Dict, Any
from beanie import PydanticObjectId
from pymongo.client_session import ClientSession
from pymongo import UpdateOne
from datetime import datetime

from app.models.org_engine.academic import AcademicYear, Semester, Department, Branch, Section
from app.models.org_engine.curriculum import Program, Course

class BaseAcademicRepository:
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


class AcademicYearRepository(BaseAcademicRepository):
    async def create(self, acy: AcademicYear, session: Optional[ClientSession] = None) -> AcademicYear:
        return await acy.insert(session=session)

    async def update(self, acy: AcademicYear, update_fields: dict, session: Optional[ClientSession] = None) -> AcademicYear:
        for key in ["_id", "id", "academic_year_id", "academicYearId", "organization_id", "organizationId", "created_at"]:
            update_fields.pop(key, None)
        
        db_update = self.map_db_fields(acy, update_fields)
        await AcademicYear.find_one(AcademicYear.id == acy.id).update({"$set": db_update}, session=session)
        self.sync_model(acy, update_fields)
        return acy

    async def delete(self, acy: AcademicYear, session: Optional[ClientSession] = None) -> bool:
        await acy.soft_delete(session=session)
        return True

    async def find_by_id(self, acy_id: str, org_id: PydanticObjectId, session: Optional[ClientSession] = None) -> Optional[AcademicYear]:
        return await AcademicYear.find_one(
            AcademicYear.academic_year_id == acy_id,
            AcademicYear.organization_id == org_id,
            AcademicYear.is_deleted == False,
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
    ) -> List[AcademicYear]:
        sort_field_map = {"createdAt": "created_at", "name": "name", "startDate": "start_date", "endDate": "end_date"}
        internal_sort = sort_field_map.get(sort_by, "created_at")
        direction = -1 if sort_order.lower() == "desc" else 1

        query = [AcademicYear.organization_id == org_id, AcademicYear.is_deleted == False]
        if filters:
            if "current" in filters:
                query.append(AcademicYear.current == filters["current"])

        cursor = AcademicYear.find(*query, session=session).sort([(internal_sort, direction)]).skip(skip).limit(limit)
        return await cursor.to_list()

    async def count(self, org_id: PydanticObjectId, filters: Optional[dict] = None, session: Optional[ClientSession] = None) -> int:
        query = [AcademicYear.organization_id == org_id, AcademicYear.is_deleted == False]
        if filters:
            if "current" in filters:
                query.append(AcademicYear.current == filters["current"])
        return await AcademicYear.find(*query, session=session).count()

    async def exists(self, org_id: PydanticObjectId, name: str, session: Optional[ClientSession] = None) -> bool:
        doc = await AcademicYear.find_one(
            AcademicYear.organization_id == org_id,
            AcademicYear.name == name,
            AcademicYear.is_deleted == False,
            session=session
        )
        return doc is not None

    async def bulk_create(self, acys: List[AcademicYear], session: Optional[ClientSession] = None) -> List[AcademicYear]:
        if not acys:
            return []
        await AcademicYear.insert_many(acys, session=session)
        return acys


class DepartmentRepository(BaseAcademicRepository):
    async def create(self, dep: Department, session: Optional[ClientSession] = None) -> Department:
        return await dep.insert(session=session)

    async def update(self, dep: Department, update_fields: dict, session: Optional[ClientSession] = None) -> Department:
        for key in ["_id", "id", "department_id", "departmentId", "organization_id", "organizationId", "created_at"]:
            update_fields.pop(key, None)
        
        db_update = self.map_db_fields(dep, update_fields)
        await Department.find_one(Department.id == dep.id).update({"$set": db_update}, session=session)
        self.sync_model(dep, update_fields)
        return dep

    async def delete(self, dep: Department, session: Optional[ClientSession] = None) -> bool:
        await dep.soft_delete(session=session)
        return True

    async def find_by_id(self, dep_id: str, org_id: PydanticObjectId, session: Optional[ClientSession] = None) -> Optional[Department]:
        return await Department.find_one(
            Department.department_id == dep_id,
            Department.organization_id == org_id,
            Department.is_deleted == False,
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
    ) -> List[Department]:
        sort_field_map = {"createdAt": "created_at", "name": "name", "code": "code"}
        internal_sort = sort_field_map.get(sort_by, "created_at")
        direction = -1 if sort_order.lower() == "desc" else 1

        query = [Department.organization_id == org_id, Department.is_deleted == False]
        if filters:
            if "status" in filters:
                query.append(Department.status == filters["status"])

        cursor = Department.find(*query, session=session).sort([(internal_sort, direction)]).skip(skip).limit(limit)
        return await cursor.to_list()

    async def count(self, org_id: PydanticObjectId, filters: Optional[dict] = None, session: Optional[ClientSession] = None) -> int:
        query = [Department.organization_id == org_id, Department.is_deleted == False]
        if filters:
            if "status" in filters:
                query.append(Department.status == filters["status"])
        return await Department.find(*query, session=session).count()

    async def exists(self, org_id: PydanticObjectId, code: str, session: Optional[ClientSession] = None) -> bool:
        doc = await Department.find_one(
            Department.organization_id == org_id,
            Department.code == code.upper(),
            Department.is_deleted == False,
            session=session
        )
        return doc is not None

    async def bulk_create(self, deps: List[Department], session: Optional[ClientSession] = None) -> List[Department]:
        if not deps:
            return []
        await Department.insert_many(deps, session=session)
        return deps


class ProgramRepository(BaseAcademicRepository):
    async def create(self, prg: Program, session: Optional[ClientSession] = None) -> Program:
        return await prg.insert(session=session)

    async def update(self, prg: Program, update_fields: dict, session: Optional[ClientSession] = None) -> Program:
        for key in ["_id", "id", "program_id", "programId", "organization_id", "organizationId", "created_at"]:
            update_fields.pop(key, None)
        
        db_update = self.map_db_fields(prg, update_fields)
        await Program.find_one(Program.id == prg.id).update({"$set": db_update}, session=session)
        self.sync_model(prg, update_fields)
        return prg

    async def delete(self, prg: Program, session: Optional[ClientSession] = None) -> bool:
        await prg.soft_delete(session=session)
        return True

    async def find_by_id(self, prg_id: str, org_id: PydanticObjectId, session: Optional[ClientSession] = None) -> Optional[Program]:
        return await Program.find_one(
            Program.program_id == prg_id,
            Program.organization_id == org_id,
            Program.is_deleted == False,
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
    ) -> List[Program]:
        sort_field_map = {"createdAt": "created_at", "name": "name", "level": "level"}
        internal_sort = sort_field_map.get(sort_by, "created_at")
        direction = -1 if sort_order.lower() == "desc" else 1

        query = [Program.organization_id == org_id, Program.is_deleted == False]
        if filters:
            if "departmentId" in filters and filters["departmentId"]:
                query.append(Program.department_id == PydanticObjectId(filters["departmentId"]))
            if "level" in filters and filters["level"]:
                query.append(Program.level == filters["level"])

        cursor = Program.find(*query, session=session).sort([(internal_sort, direction)]).skip(skip).limit(limit)
        return await cursor.to_list()

    async def count(self, org_id: PydanticObjectId, filters: Optional[dict] = None, session: Optional[ClientSession] = None) -> int:
        query = [Program.organization_id == org_id, Program.is_deleted == False]
        if filters:
            if "departmentId" in filters and filters["departmentId"]:
                query.append(Program.department_id == PydanticObjectId(filters["departmentId"]))
            if "level" in filters and filters["level"]:
                query.append(Program.level == filters["level"])
        return await Program.find(*query, session=session).count()

    async def exists(self, org_id: PydanticObjectId, department_id: PydanticObjectId, name: str, session: Optional[ClientSession] = None) -> bool:
        doc = await Program.find_one(
            Program.organization_id == org_id,
            Program.department_id == department_id,
            Program.name == name,
            Program.is_deleted == False,
            session=session
        )
        return doc is not None

    async def bulk_create(self, prgs: List[Program], session: Optional[ClientSession] = None) -> List[Program]:
        if not prgs:
            return []
        await Program.insert_many(prgs, session=session)
        return prgs


class BranchRepository(BaseAcademicRepository):
    async def create(self, brn: Branch, session: Optional[ClientSession] = None) -> Branch:
        return await brn.insert(session=session)

    async def update(self, brn: Branch, update_fields: dict, session: Optional[ClientSession] = None) -> Branch:
        for key in ["_id", "id", "branch_id", "branchId", "organization_id", "organizationId", "created_at"]:
            update_fields.pop(key, None)
        
        db_update = self.map_db_fields(brn, update_fields)
        await Branch.find_one(Branch.id == brn.id).update({"$set": db_update}, session=session)
        self.sync_model(brn, update_fields)
        return brn

    async def delete(self, brn: Branch, session: Optional[ClientSession] = None) -> bool:
        await brn.soft_delete(session=session)
        return True

    async def find_by_id(self, brn_id: str, org_id: PydanticObjectId, session: Optional[ClientSession] = None) -> Optional[Branch]:
        return await Branch.find_one(
            Branch.branch_id == brn_id,
            Branch.organization_id == org_id,
            Branch.is_deleted == False,
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
    ) -> List[Branch]:
        sort_field_map = {"createdAt": "created_at", "name": "name", "code": "code"}
        internal_sort = sort_field_map.get(sort_by, "created_at")
        direction = -1 if sort_order.lower() == "desc" else 1

        query = [Branch.organization_id == org_id, Branch.is_deleted == False]
        if filters:
            if "departmentId" in filters and filters["departmentId"]:
                query.append(Branch.department_id == PydanticObjectId(filters["departmentId"]))

        cursor = Branch.find(*query, session=session).sort([(internal_sort, direction)]).skip(skip).limit(limit)
        return await cursor.to_list()

    async def count(self, org_id: PydanticObjectId, filters: Optional[dict] = None, session: Optional[ClientSession] = None) -> int:
        query = [Branch.organization_id == org_id, Branch.is_deleted == False]
        if filters:
            if "departmentId" in filters and filters["departmentId"]:
                query.append(Branch.department_id == PydanticObjectId(filters["departmentId"]))
        return await Branch.find(*query, session=session).count()

    async def exists(self, department_id: PydanticObjectId, code: str, session: Optional[ClientSession] = None) -> bool:
        doc = await Branch.find_one(
            Branch.department_id == department_id,
            Branch.code == code.upper(),
            Branch.is_deleted == False,
            session=session
        )
        return doc is not None

    async def bulk_create(self, brns: List[Branch], session: Optional[ClientSession] = None) -> List[Branch]:
        if not brns:
            return []
        await Branch.insert_many(brns, session=session)
        return brns


class SemesterRepository(BaseAcademicRepository):
    async def create(self, sem: Semester, session: Optional[ClientSession] = None) -> Semester:
        return await sem.insert(session=session)

    async def update(self, sem: Semester, update_fields: dict, session: Optional[ClientSession] = None) -> Semester:
        for key in ["_id", "id", "semester_id", "semesterId", "organization_id", "organizationId", "created_at"]:
            update_fields.pop(key, None)
        
        db_update = self.map_db_fields(sem, update_fields)
        await Semester.find_one(Semester.id == sem.id).update({"$set": db_update}, session=session)
        self.sync_model(sem, update_fields)
        return sem

    async def delete(self, sem: Semester, session: Optional[ClientSession] = None) -> bool:
        await sem.soft_delete(session=session)
        return True

    async def find_by_id(self, sem_id: str, org_id: PydanticObjectId, session: Optional[ClientSession] = None) -> Optional[Semester]:
        return await Semester.find_one(
            Semester.semester_id == sem_id,
            Semester.organization_id == org_id,
            Semester.is_deleted == False,
            session=session
        )

    async def list(
        self,
        org_id: PydanticObjectId,
        skip: int = 0,
        limit: int = 10,
        sort_by: str = "number",
        sort_order: str = "asc",
        filters: Optional[dict] = None,
        session: Optional[ClientSession] = None
    ) -> List[Semester]:
        sort_field_map = {"createdAt": "created_at", "name": "name", "number": "number"}
        internal_sort = sort_field_map.get(sort_by, "number")
        direction = -1 if sort_order.lower() == "desc" else 1

        query = [Semester.organization_id == org_id, Semester.is_deleted == False]
        if filters:
            if "status" in filters:
                query.append(Semester.status == filters["status"])

        cursor = Semester.find(*query, session=session).sort([(internal_sort, direction)]).skip(skip).limit(limit)
        return await cursor.to_list()

    async def count(self, org_id: PydanticObjectId, filters: Optional[dict] = None, session: Optional[ClientSession] = None) -> int:
        query = [Semester.organization_id == org_id, Semester.is_deleted == False]
        if filters:
            if "status" in filters:
                query.append(Semester.status == filters["status"])
        return await Semester.find(*query, session=session).count()

    async def exists(self, org_id: PydanticObjectId, number: int, session: Optional[ClientSession] = None) -> bool:
        doc = await Semester.find_one(
            Semester.organization_id == org_id,
            Semester.number == number,
            Semester.is_deleted == False,
            session=session
        )
        return doc is not None

    async def bulk_create(self, sems: List[Semester], session: Optional[ClientSession] = None) -> List[Semester]:
        if not sems:
            return []
        await Semester.insert_many(sems, session=session)
        return sems


class SectionRepository(BaseAcademicRepository):
    async def create(self, sec: Section, session: Optional[ClientSession] = None) -> Section:
        return await sec.insert(session=session)

    async def update(self, sec: Section, update_fields: dict, session: Optional[ClientSession] = None) -> Section:
        for key in ["_id", "id", "section_id", "sectionId", "organization_id", "organizationId", "created_at"]:
            update_fields.pop(key, None)
        
        db_update = self.map_db_fields(sec, update_fields)
        await Section.find_one(Section.id == sec.id).update({"$set": db_update}, session=session)
        self.sync_model(sec, update_fields)
        return sec

    async def delete(self, sec: Section, session: Optional[ClientSession] = None) -> bool:
        await sec.soft_delete(session=session)
        return True

    async def find_by_id(self, sec_id: str, org_id: PydanticObjectId, session: Optional[ClientSession] = None) -> Optional[Section]:
        return await Section.find_one(
            Section.section_id == sec_id,
            Section.organization_id == org_id,
            Section.is_deleted == False,
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
    ) -> List[Section]:
        sort_field_map = {"createdAt": "created_at", "name": "name", "strength": "strength"}
        internal_sort = sort_field_map.get(sort_by, "created_at")
        direction = -1 if sort_order.lower() == "desc" else 1

        query = [Section.organization_id == org_id, Section.is_deleted == False]
        if filters:
            if "branchId" in filters and filters["branchId"]:
                query.append(Section.branch_id == PydanticObjectId(filters["branchId"]))
            if "semesterId" in filters and filters["semesterId"]:
                query.append(Section.semester_id == PydanticObjectId(filters["semesterId"]))

        cursor = Section.find(*query, session=session).sort([(internal_sort, direction)]).skip(skip).limit(limit)
        return await cursor.to_list()

    async def count(self, org_id: PydanticObjectId, filters: Optional[dict] = None, session: Optional[ClientSession] = None) -> int:
        query = [Section.organization_id == org_id, Section.is_deleted == False]
        if filters:
            if "branchId" in filters and filters["branchId"]:
                query.append(Section.branch_id == PydanticObjectId(filters["branchId"]))
            if "semesterId" in filters and filters["semesterId"]:
                query.append(Section.semester_id == PydanticObjectId(filters["semesterId"]))
        return await Section.find(*query, session=session).count()

    async def exists(self, branch_id: PydanticObjectId, semester_id: PydanticObjectId, name: str, session: Optional[ClientSession] = None) -> bool:
        doc = await Section.find_one(
            Section.branch_id == branch_id,
            Section.semester_id == semester_id,
            Section.name == name,
            Section.is_deleted == False,
            session=session
        )
        return doc is not None

    async def bulk_create(self, secs: List[Section], session: Optional[ClientSession] = None) -> List[Section]:
        if not secs:
            return []
        await Section.insert_many(secs, session=session)
        return secs


class CourseRepository(BaseAcademicRepository):
    async def create(self, crs: Course, session: Optional[ClientSession] = None) -> Course:
        return await crs.insert(session=session)

    async def update(self, crs: Course, update_fields: dict, session: Optional[ClientSession] = None) -> Course:
        for key in ["_id", "id", "course_id", "courseId", "organization_id", "organizationId", "created_at"]:
            update_fields.pop(key, None)
        
        db_update = self.map_db_fields(crs, update_fields)
        await Course.find_one(Course.id == crs.id).update({"$set": db_update}, session=session)
        self.sync_model(crs, update_fields)
        return crs

    async def delete(self, crs: Course, session: Optional[ClientSession] = None) -> bool:
        await crs.soft_delete(session=session)
        return True

    async def find_by_id(self, crs_id: str, org_id: PydanticObjectId, session: Optional[ClientSession] = None) -> Optional[Course]:
        return await Course.find_one(
            Course.course_id == crs_id,
            Course.organization_id == org_id,
            Course.is_deleted == False,
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
    ) -> List[Course]:
        sort_field_map = {"createdAt": "created_at", "courseCode": "course_code", "credits": "credits"}
        internal_sort = sort_field_map.get(sort_by, "created_at")
        direction = -1 if sort_order.lower() == "desc" else 1

        query = [Course.organization_id == org_id, Course.is_deleted == False]
        if filters:
            if "programId" in filters and filters["programId"]:
                query.append(Course.program_id == PydanticObjectId(filters["programId"]))
            if "semester" in filters and filters["semester"]:
                query.append(Course.semester == filters["semester"])

        cursor = Course.find(*query, session=session).sort([(internal_sort, direction)]).skip(skip).limit(limit)
        return await cursor.to_list()

    async def count(self, org_id: PydanticObjectId, filters: Optional[dict] = None, session: Optional[ClientSession] = None) -> int:
        query = [Course.organization_id == org_id, Course.is_deleted == False]
        if filters:
            if "programId" in filters and filters["programId"]:
                query.append(Course.program_id == PydanticObjectId(filters["programId"]))
            if "semester" in filters and filters["semester"]:
                query.append(Course.semester == filters["semester"])
        return await Course.find(*query, session=session).count()

    async def exists(self, org_id: PydanticObjectId, course_code: str, session: Optional[ClientSession] = None) -> bool:
        doc = await Course.find_one(
            Course.organization_id == org_id,
            Course.course_code == course_code.upper(),
            Course.is_deleted == False,
            session=session
        )
        return doc is not None

    async def bulk_create(self, crss: List[Course], session: Optional[ClientSession] = None) -> List[Course]:
        if not crss:
            return []
        await Course.insert_many(crss, session=session)
        return crss
