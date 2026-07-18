from typing import List, Optional, Tuple, Dict, Any
from beanie import PydanticObjectId
from app.student.models import Student, Guardian, StudentDocument, StudentAchievement, StudentSkill

class StudentRepository:
    async def create(self, student: Student) -> Student:
        return await student.insert()

    async def get_by_id(self, id: PydanticObjectId, org_id: PydanticObjectId) -> Optional[Student]:
        return await Student.find_one(
            Student.id == id,
            Student.organization_id == org_id,
            Student.is_deleted == False
        )

    async def get_by_student_id(self, student_id: str, org_id: PydanticObjectId) -> Optional[Student]:
        return await Student.find_one(
            Student.student_id == student_id,
            Student.organization_id == org_id,
            Student.is_deleted == False
        )

    async def get_by_roll_number(self, roll_number: str, org_id: PydanticObjectId) -> Optional[Student]:
        return await Student.find_one(
            Student.roll_number == roll_number,
            Student.organization_id == org_id,
            Student.is_deleted == False
        )

    async def list_students(
        self,
        org_id: PydanticObjectId,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Student], int]:
        query = {
            "organizationId": org_id,
            "isDeleted": False
        }
        
        if filters:
            if filters.get("status"):
                query["status"] = filters["status"]
            if filters.get("academic_year_id"):
                query["academicYearId"] = PydanticObjectId(filters["academic_year_id"])
            if filters.get("semester_id"):
                query["semesterId"] = PydanticObjectId(filters["semester_id"])
            if filters.get("branch_id"):
                query["branchId"] = PydanticObjectId(filters["branch_id"])
            if filters.get("search_query"):
                # Use Text search OR fallback regex match
                search = filters["search_query"]
                query["$or"] = [
                    {"firstName": {"$regex": search, "$options": "i"}},
                    {"lastName": {"$regex": search, "$options": "i"}},
                    {"email": {"$regex": search, "$options": "i"}},
                    {"rollNumber": {"$regex": search, "$options": "i"}}
                ]

        total = await Student.find(query).count()
        results = await Student.find(query).skip(skip).limit(limit).to_list()
        return results, total

    async def update(self, student: Student) -> Student:
        return await student.save()


class GuardianRepository:
    async def create(self, guardian: Guardian) -> Guardian:
        return await guardian.insert()

    async def get_by_id(self, id: PydanticObjectId, student_id: PydanticObjectId, org_id: PydanticObjectId) -> Optional[Guardian]:
        return await Guardian.find_one(
            Guardian.id == id,
            Guardian.student_id == student_id,
            Guardian.organization_id == org_id,
            Guardian.is_deleted == False
        )

    async def get_by_guardian_id(self, guardian_id: str, student_id: PydanticObjectId, org_id: PydanticObjectId) -> Optional[Guardian]:
        return await Guardian.find_one(
            Guardian.guardian_id == guardian_id,
            Guardian.student_id == student_id,
            Guardian.organization_id == org_id,
            Guardian.is_deleted == False
        )

    async def list_guardians(self, student_id: PydanticObjectId, org_id: PydanticObjectId) -> List[Guardian]:
        return await Guardian.find(
            Guardian.student_id == student_id,
            Guardian.organization_id == org_id,
            Guardian.is_deleted == False
        ).to_list()

    async def update(self, guardian: Guardian) -> Guardian:
        return await guardian.save()


class DocumentRepository:
    async def create(self, doc: StudentDocument) -> StudentDocument:
        return await doc.insert()

    async def get_by_id(self, id: PydanticObjectId, student_id: PydanticObjectId, org_id: PydanticObjectId) -> Optional[StudentDocument]:
        return await StudentDocument.find_one(
            StudentDocument.id == id,
            StudentDocument.student_id == student_id,
            StudentDocument.organization_id == org_id,
            StudentDocument.is_deleted == False
        )

    async def get_by_document_id(self, document_id: str, student_id: PydanticObjectId, org_id: PydanticObjectId) -> Optional[StudentDocument]:
        return await StudentDocument.find_one(
            StudentDocument.document_id == document_id,
            StudentDocument.student_id == student_id,
            StudentDocument.organization_id == org_id,
            StudentDocument.is_deleted == False
        )

    async def list_documents(self, student_id: PydanticObjectId, org_id: PydanticObjectId) -> List[StudentDocument]:
        return await StudentDocument.find(
            StudentDocument.student_id == student_id,
            StudentDocument.organization_id == org_id,
            StudentDocument.is_deleted == False
        ).to_list()


class AchievementRepository:
    async def create(self, ach: StudentAchievement) -> StudentAchievement:
        return await ach.insert()

    async def get_by_id(self, id: PydanticObjectId, student_id: PydanticObjectId, org_id: PydanticObjectId) -> Optional[StudentAchievement]:
        return await StudentAchievement.find_one(
            StudentAchievement.id == id,
            StudentAchievement.student_id == student_id,
            StudentAchievement.organization_id == org_id,
            StudentAchievement.is_deleted == False
        )

    async def get_by_achievement_id(self, achievement_id: str, student_id: PydanticObjectId, org_id: PydanticObjectId) -> Optional[StudentAchievement]:
        return await StudentAchievement.find_one(
            StudentAchievement.achievement_id == achievement_id,
            StudentAchievement.student_id == student_id,
            StudentAchievement.organization_id == org_id,
            StudentAchievement.is_deleted == False
        )

    async def list_achievements(self, student_id: PydanticObjectId, org_id: PydanticObjectId) -> List[StudentAchievement]:
        return await StudentAchievement.find(
            StudentAchievement.student_id == student_id,
            StudentAchievement.organization_id == org_id,
            StudentAchievement.is_deleted == False
        ).to_list()


class SkillRepository:
    async def create(self, skill: StudentSkill) -> StudentSkill:
        return await skill.insert()

    async def get_by_id(self, id: PydanticObjectId, student_id: PydanticObjectId, org_id: PydanticObjectId) -> Optional[StudentSkill]:
        return await StudentSkill.find_one(
            StudentSkill.id == id,
            StudentSkill.student_id == student_id,
            StudentSkill.organization_id == org_id,
            StudentSkill.is_deleted == False
        )

    async def get_by_skill_id(self, skill_id: str, student_id: PydanticObjectId, org_id: PydanticObjectId) -> Optional[StudentSkill]:
        return await StudentSkill.find_one(
            StudentSkill.skill_id == skill_id,
            StudentSkill.student_id == student_id,
            StudentSkill.organization_id == org_id,
            StudentSkill.is_deleted == False
        )

    async def list_skills(self, student_id: PydanticObjectId, org_id: PydanticObjectId) -> List[StudentSkill]:
        return await StudentSkill.find(
            StudentSkill.student_id == student_id,
            StudentSkill.organization_id == org_id,
            StudentSkill.is_deleted == False
        ).to_list()
