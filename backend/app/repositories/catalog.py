from typing import List, Optional, Dict, Any
from beanie import PydanticObjectId
from pymongo.client_session import ClientSession

from app.models.catalog.curriculum import Curriculum, CurriculumStatus
from app.models.catalog.subject import Subject


class BaseCatalogRepository:
    """Shared utilities for catalog repositories — mirrors BaseAcademicRepository pattern."""

    @staticmethod
    def sync_model(model: Any, update_fields: dict) -> None:
        field_mapping = {}
        for name, field in model.model_fields.items():
            field_mapping[name] = name
            if field.alias:
                field_mapping[field.alias] = name
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


class CurriculumRepository(BaseCatalogRepository):
    async def create(
        self, curriculum: Curriculum, session: Optional[ClientSession] = None
    ) -> Curriculum:
        return await curriculum.insert(session=session)

    async def update(
        self,
        curriculum: Curriculum,
        update_fields: dict,
        session: Optional[ClientSession] = None,
    ) -> Curriculum:
        for key in ["_id", "id", "curriculum_id", "curriculumId", "organization_id",
                    "organizationId", "created_at", "version", "status"]:
            update_fields.pop(key, None)
        db_update = self.map_db_fields(curriculum, update_fields)
        await Curriculum.find_one(Curriculum.id == curriculum.id).update(
            {"$set": db_update}, session=session
        )
        self.sync_model(curriculum, update_fields)
        return curriculum

    async def update_status(
        self,
        curriculum: Curriculum,
        status: CurriculumStatus,
        session: Optional[ClientSession] = None,
    ) -> Curriculum:
        await Curriculum.find_one(Curriculum.id == curriculum.id).update(
            {"$set": {"status": status.value}}, session=session
        )
        curriculum.status = status
        return curriculum

    async def update_total_credits(
        self,
        curriculum: Curriculum,
        total_credits: float,
        session: Optional[ClientSession] = None,
    ) -> Curriculum:
        await Curriculum.find_one(Curriculum.id == curriculum.id).update(
            {"$set": {"totalCredits": total_credits}}, session=session
        )
        curriculum.total_credits = total_credits
        return curriculum

    async def delete(
        self, curriculum: Curriculum, session: Optional[ClientSession] = None
    ) -> bool:
        await curriculum.soft_delete(session=session)
        return True

    async def find_by_id(
        self,
        curriculum_id: str,
        org_id: PydanticObjectId,
        session: Optional[ClientSession] = None,
    ) -> Optional[Curriculum]:
        return await Curriculum.find_one(
            Curriculum.curriculum_id == curriculum_id,
            Curriculum.organization_id == org_id,
            Curriculum.is_deleted == False,
            session=session,
        )

    async def find_by_object_id(
        self,
        curriculum_oid: PydanticObjectId,
        org_id: PydanticObjectId,
        session: Optional[ClientSession] = None,
    ) -> Optional[Curriculum]:
        return await Curriculum.find_one(
            Curriculum.id == curriculum_oid,
            Curriculum.organization_id == org_id,
            Curriculum.is_deleted == False,
            session=session,
        )

    async def list(
        self,
        org_id: PydanticObjectId,
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "createdAt",
        sort_order: str = "desc",
        filters: Optional[dict] = None,
        session: Optional[ClientSession] = None,
    ) -> List[Curriculum]:
        sort_field_map = {
            "createdAt": "created_at",
            "name": "name",
            "version": "version",
            "status": "status",
        }
        internal_sort = sort_field_map.get(sort_by, "created_at")
        direction = -1 if sort_order.lower() == "desc" else 1

        query = [Curriculum.organization_id == org_id, Curriculum.is_deleted == False]
        if filters:
            if filters.get("programId"):
                query.append(Curriculum.program_id == PydanticObjectId(filters["programId"]))
            if filters.get("status"):
                query.append(Curriculum.status == filters["status"])

        cursor = (
            Curriculum.find(*query, session=session)
            .sort([(internal_sort, direction)])
            .skip(skip)
            .limit(limit)
        )
        return await cursor.to_list()

    async def count(
        self,
        org_id: PydanticObjectId,
        filters: Optional[dict] = None,
        session: Optional[ClientSession] = None,
    ) -> int:
        query = [Curriculum.organization_id == org_id, Curriculum.is_deleted == False]
        if filters:
            if filters.get("programId"):
                query.append(Curriculum.program_id == PydanticObjectId(filters["programId"]))
            if filters.get("status"):
                query.append(Curriculum.status == filters["status"])
        return await Curriculum.find(*query, session=session).count()

    async def exists_version(
        self,
        org_id: PydanticObjectId,
        program_id: PydanticObjectId,
        version: int,
        session: Optional[ClientSession] = None,
    ) -> bool:
        doc = await Curriculum.find_one(
            Curriculum.organization_id == org_id,
            Curriculum.program_id == program_id,
            Curriculum.version == version,
            Curriculum.is_deleted == False,
            session=session,
        )
        return doc is not None

    async def get_max_version(
        self,
        org_id: PydanticObjectId,
        program_id: PydanticObjectId,
        session: Optional[ClientSession] = None,
    ) -> int:
        """Return the highest version number for a given program."""
        docs = await (
            Curriculum.find(
                Curriculum.organization_id == org_id,
                Curriculum.program_id == program_id,
                Curriculum.is_deleted == False,
                session=session,
            )
            .sort([("version", -1)])
            .limit(1)
            .to_list()
        )
        if not docs:
            return 0
        return docs[0].version


class SubjectRepository(BaseCatalogRepository):
    async def create(
        self, subject: Subject, session: Optional[ClientSession] = None
    ) -> Subject:
        return await subject.insert(session=session)

    async def bulk_create(
        self, subjects: List[Subject], session: Optional[ClientSession] = None
    ) -> List[Subject]:
        if not subjects:
            return []
        await Subject.insert_many(subjects, session=session)
        return subjects

    async def update(
        self,
        subject: Subject,
        update_fields: dict,
        session: Optional[ClientSession] = None,
    ) -> Subject:
        for key in ["_id", "id", "subject_id", "subjectId", "organization_id",
                    "organizationId", "curriculum_id", "curriculumId", "created_at"]:
            update_fields.pop(key, None)
        db_update = self.map_db_fields(subject, update_fields)
        await Subject.find_one(Subject.id == subject.id).update(
            {"$set": db_update}, session=session
        )
        self.sync_model(subject, update_fields)
        return subject

    async def delete(
        self, subject: Subject, session: Optional[ClientSession] = None
    ) -> bool:
        await subject.soft_delete(session=session)
        return True

    async def find_by_id(
        self,
        subject_id: str,
        curriculum_id: PydanticObjectId,
        org_id: PydanticObjectId,
        session: Optional[ClientSession] = None,
    ) -> Optional[Subject]:
        return await Subject.find_one(
            Subject.subject_id == subject_id,
            Subject.curriculum_id == curriculum_id,
            Subject.organization_id == org_id,
            Subject.is_deleted == False,
            session=session,
        )

    async def find_by_id_global(
        self,
        subject_id: str,
        org_id: PydanticObjectId,
        session: Optional[ClientSession] = None,
    ) -> Optional[Subject]:
        """Find subject by subject_id without requiring curriculum context."""
        return await Subject.find_one(
            Subject.subject_id == subject_id,
            Subject.organization_id == org_id,
            Subject.is_deleted == False,
            session=session,
        )

    async def list_by_curriculum(
        self,
        curriculum_id: PydanticObjectId,
        org_id: PydanticObjectId,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "semesterNumber",
        sort_order: str = "asc",
        filters: Optional[dict] = None,
        session: Optional[ClientSession] = None,
    ) -> List[Subject]:
        sort_field_map = {
            "semesterNumber": "semester_number",
            "name": "name",
            "credits": "credits",
            "subjectCode": "subject_code",
            "createdAt": "created_at",
        }
        internal_sort = sort_field_map.get(sort_by, "semester_number")
        direction = -1 if sort_order.lower() == "desc" else 1

        query = [
            Subject.curriculum_id == curriculum_id,
            Subject.organization_id == org_id,
            Subject.is_deleted == False,
        ]
        if filters:
            if filters.get("semesterNumber") is not None:
                query.append(Subject.semester_number == filters["semesterNumber"])
            if filters.get("subjectType"):
                query.append(Subject.subject_type == filters["subjectType"])

        cursor = (
            Subject.find(*query, session=session)
            .sort([(internal_sort, direction)])
            .skip(skip)
            .limit(limit)
        )
        return await cursor.to_list()

    async def find_all_by_curriculum(
        self,
        curriculum_id: PydanticObjectId,
        org_id: PydanticObjectId,
        session: Optional[ClientSession] = None,
    ) -> List[Subject]:
        """Fetch ALL subjects in a curriculum — used for graph operations and cloning."""
        return await Subject.find(
            Subject.curriculum_id == curriculum_id,
            Subject.organization_id == org_id,
            Subject.is_deleted == False,
            session=session,
        ).to_list()

    async def count_by_curriculum(
        self,
        curriculum_id: PydanticObjectId,
        org_id: PydanticObjectId,
        session: Optional[ClientSession] = None,
    ) -> int:
        return await Subject.find(
            Subject.curriculum_id == curriculum_id,
            Subject.organization_id == org_id,
            Subject.is_deleted == False,
            session=session,
        ).count()

    async def exists(
        self,
        curriculum_id: PydanticObjectId,
        subject_code: str,
        session: Optional[ClientSession] = None,
    ) -> bool:
        doc = await Subject.find_one(
            Subject.curriculum_id == curriculum_id,
            Subject.subject_code == subject_code.upper(),
            Subject.is_deleted == False,
            session=session,
        )
        return doc is not None

    async def find_subjects_with_prerequisite(
        self,
        subject_id: str,
        curriculum_id: PydanticObjectId,
        session: Optional[ClientSession] = None,
    ) -> List[Subject]:
        """Find all subjects that list subject_id as a prerequisite."""
        return await Subject.find(
            Subject.curriculum_id == curriculum_id,
            Subject.prerequisites == subject_id,
            Subject.is_deleted == False,
            session=session,
        ).to_list()
