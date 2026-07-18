import random
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from beanie import PydanticObjectId

from app.student.models import (
    Student, Guardian, StudentDocument, StudentAchievement, StudentSkill, 
    StudentStatus, DocumentCategory, AchievementCategory, SkillLevel, 
    EmergencyContact, StudentPreference, StudentNote
)
from app.student.repository import (
    StudentRepository, GuardianRepository, DocumentRepository, 
    AchievementRepository, SkillRepository
)
from app.student.exceptions import (
    StudentNotFound, DuplicateRollNumber, StudentArchivedReadOnly, 
    GuardianLimitExceeded, GuardianNotFound, DocumentNotFound, 
    AchievementNotFound, SkillNotFound
)
from app.models.identity.user import User, UserStatus, AccountType
from app.academic.validation import AcademicValidationPipeline

class StudentService:
    def __init__(
        self,
        student_repo: Optional[StudentRepository] = None,
        guardian_repo: Optional[GuardianRepository] = None
    ):
        self.student_repo = student_repo or StudentRepository()
        self.guardian_repo = guardian_repo or GuardianRepository()

    async def _generate_unique_id(self, prefix: str, model_cls, id_field: str) -> str:
        for _ in range(20):
            digits = "".join(str(random.randint(0, 9)) for _ in range(6))
            candidate = f"{prefix}_{digits}"
            # Check existence using raw dict query
            exists = await model_cls.find_one({id_field: candidate})
            if not exists:
                return candidate
        return f"{prefix}_{random.randint(100000, 999999)}"

    async def create_student(self, org_id: PydanticObjectId, payload: Dict[str, Any]) -> Student:
        # 1. Check unique roll number
        roll = payload.get("rollNumber") or payload.get("roll_number")
        existing = await self.student_repo.get_by_roll_number(roll, org_id)
        if existing:
            raise DuplicateRollNumber()

        # 2. Validate academic coordinates
        await AcademicValidationPipeline.validate_academic_hierarchy(
            org_id=org_id,
            department_id=payload.get("departmentId"),
            program_id=payload.get("programId"),
            branch_id=payload.get("branchId"),
            semester_id=payload.get("semesterId"),
            section_id=payload.get("sectionId")
        )

        # 3. Handle Identity User Reference
        email = payload.get("email").lower()
        user = await User.find_one(User.email == email)
        if not user:
            # Create a placeholder user
            usr_id = await self._generate_unique_id("USR", User, "userId")
            username = email.split("@")[0]
            # Verify username unique
            existing_user = await User.find_one(User.username == username)
            if existing_user:
                username = f"{username}_{random.randint(10, 99)}"
                
            user = User(
                userId=usr_id,
                organizationId=org_id,
                username=username,
                email=email,
                status=UserStatus.ACTIVE,
                accountType=AccountType.STUDENT
            )
            await user.insert()

        # 4. Generate Student ID
        stu_id = await self._generate_unique_id("STU", Student, "studentId")

        # 5. Build Student
        emergency = None
        if payload.get("emergencyContact"):
            em_payload = payload["emergencyContact"]
            emergency = EmergencyContact(
                name=em_payload.get("name"),
                relation=em_payload.get("relation"),
                phone=em_payload.get("phone"),
                alternativePhone=em_payload.get("alternativePhone"),
                email=em_payload.get("email")
            )

        student = Student(
            studentId=stu_id,
            userId=user.id,
            organizationId=org_id,
            rollNumber=roll,
            firstName=payload.get("firstName") or payload.get("first_name"),
            lastName=payload.get("lastName") or payload.get("last_name"),
            email=email,
            phone=payload.get("phone"),
            dateOfBirth=payload.get("dateOfBirth") or payload.get("date_of_birth"),
            gender=payload.get("gender"),
            bloodGroup=payload.get("bloodGroup") or payload.get("blood_group"),
            admissionDate=payload.get("admissionDate") or payload.get("admission_date") or datetime.utcnow(),
            status=StudentStatus.ACTIVE,
            academicYearId=payload.get("academicYearId"),
            departmentId=payload.get("departmentId"),
            program_id=payload.get("programId"),
            branchId=payload.get("branchId"),
            semesterId=payload.get("semesterId"),
            sectionId=payload.get("sectionId"),
            emergencyContact=emergency,
            tags=payload.get("tags") or [],
            notes=[]
        )

        return await self.student_repo.create(student)

    async def update_student(self, student_id: str, org_id: PydanticObjectId, payload: Dict[str, Any]) -> Student:
        student = await self.student_repo.get_by_student_id(student_id, org_id)
        if not student:
            raise StudentNotFound()

        if student.status == StudentStatus.ARCHIVED or student.is_archived:
            raise StudentArchivedReadOnly()

        # Check roll number update
        roll = payload.get("rollNumber") or payload.get("roll_number")
        if roll and roll != student.roll_number:
            existing = await self.student_repo.get_by_roll_number(roll, org_id)
            if existing:
                raise DuplicateRollNumber()
            student.roll_number = roll

        # Validate academic coordinates if changed
        dept_id = payload.get("departmentId") or student.department_id
        prog_id = payload.get("programId") or student.program_id
        brn_id = payload.get("branchId") or student.branch_id
        sem_id = payload.get("semesterId") or student.semester_id
        sec_id = payload.get("sectionId") or student.section_id

        await AcademicValidationPipeline.validate_academic_hierarchy(
            org_id=org_id,
            department_id=dept_id,
            program_id=prog_id,
            branch_id=brn_id,
            semester_id=sem_id,
            section_id=sec_id
        )

        # Update fields
        if payload.get("firstName") or payload.get("first_name"):
            student.first_name = payload.get("firstName") or payload.get("first_name")
        if payload.get("lastName") or payload.get("last_name"):
            student.last_name = payload.get("lastName") or payload.get("last_name")
        if payload.get("phone"):
            student.phone = payload.get("phone")
        if payload.get("gender"):
            student.gender = payload.get("gender")
        if payload.get("bloodGroup") or payload.get("blood_group"):
            student.blood_group = payload.get("bloodGroup") or payload.get("blood_group")
        if payload.get("dateOfBirth") or payload.get("date_of_birth"):
            student.date_of_birth = payload.get("dateOfBirth") or payload.get("date_of_birth")
        if "tags" in payload:
            student.tags = payload["tags"]

        # Embedded changes
        if payload.get("emergencyContact"):
            em_payload = payload["emergencyContact"]
            student.emergency_contact = EmergencyContact(
                name=em_payload.get("name"),
                relation=em_payload.get("relation"),
                phone=em_payload.get("phone"),
                alternativePhone=em_payload.get("alternativePhone"),
                email=em_payload.get("email")
            )

        student.department_id = dept_id
        student.program_id = prog_id
        student.branch_id = brn_id
        student.semester_id = sem_id
        student.section_id = sec_id

        if payload.get("status"):
            student.status = StudentStatus(payload["status"])

        return await self.student_repo.update(student)

    async def archive_student(self, student_id: str, org_id: PydanticObjectId) -> Student:
        student = await self.student_repo.get_by_student_id(student_id, org_id)
        if not student:
            raise StudentNotFound()

        student.status = StudentStatus.ARCHIVED
        student.is_archived = True
        return await self.student_repo.update(student)

    async def restore_student(self, student_id: str, org_id: PydanticObjectId) -> Student:
        student = await self.student_repo.get_by_student_id(student_id, org_id)
        if not student:
            raise StudentNotFound()

        student.status = StudentStatus.ACTIVE
        student.is_archived = False
        return await self.student_repo.update(student)

    async def add_note(self, student_id: str, org_id: PydanticObjectId, author: str, content: str) -> Student:
        student = await self.student_repo.get_by_student_id(student_id, org_id)
        if not student:
            raise StudentNotFound()
        
        note = StudentNote(
            noteId=f"NTE_{random.randint(100000, 999999)}",
            author=author,
            content=content,
            createdAt=datetime.utcnow()
        )
        student.notes.append(note)
        return await self.student_repo.update(student)

    async def bulk_import_students(self, org_id: PydanticObjectId, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        success_count = 0
        failed = []

        for idx, rec in enumerate(records):
            try:
                # Basic requirements
                email = rec.get("email")
                roll = rec.get("rollNumber") or rec.get("roll_number")
                first = rec.get("firstName") or rec.get("first_name")
                last = rec.get("lastName") or rec.get("last_name")
                dob_str = rec.get("dateOfBirth") or rec.get("date_of_birth")
                gender = rec.get("gender")

                if not (email and roll and first and last and dob_str and gender):
                    raise ValueError("Missing critical fields (email, rollNumber, name, dob, gender)")

                # Parse DOB
                try:
                    dob = datetime.fromisoformat(dob_str.replace("Z", ""))
                except Exception:
                    dob = datetime.strptime(dob_str, "%Y-%m-%d")

                payload = {
                    **rec,
                    "dateOfBirth": dob,
                    "email": email,
                    "rollNumber": roll,
                    "firstName": first,
                    "lastName": last,
                    "gender": gender
                }
                
                # Create student
                await self.create_student(org_id, payload)
                success_count += 1
            except Exception as e:
                failed.append({
                    "row": idx + 1,
                    "rollNumber": rec.get("rollNumber") or rec.get("roll_number") or "Unknown",
                    "error": str(e)
                })

        return {
            "successCount": success_count,
            "failedCount": len(failed),
            "errors": failed
        }


class ProfileService:
    def __init__(
        self,
        student_repo: Optional[StudentRepository] = None,
        guardian_repo: Optional[GuardianRepository] = None,
        doc_repo: Optional[DocumentRepository] = None,
        ach_repo: Optional[AchievementRepository] = None,
        skl_repo: Optional[SkillRepository] = None
    ):
        self.student_repo = student_repo or StudentRepository()
        self.guardian_repo = guardian_repo or GuardianRepository()
        self.doc_repo = doc_repo or DocumentRepository()
        self.ach_repo = ach_repo or AchievementRepository()
        self.skl_repo = skl_repo or SkillRepository()

    async def _verify_write_permission(self, student_id: str, org_id: PydanticObjectId) -> Student:
        student = await self.student_repo.get_by_student_id(student_id, org_id)
        if not student:
            raise StudentNotFound()
        if student.status == StudentStatus.ARCHIVED or student.is_archived:
            raise StudentArchivedReadOnly()
        return student

    async def _generate_unique_id(self, prefix: str, model_cls, id_field: str) -> str:
        for _ in range(20):
            digits = "".join(str(random.randint(0, 9)) for _ in range(6))
            candidate = f"{prefix}_{digits}"
            exists = await model_cls.find_one({id_field: candidate})
            if not exists:
                return candidate
        return f"{prefix}_{random.randint(100000, 999999)}"

    # ── Guardians ─────────────────────────────────────────────────────────────
    async def add_guardian(self, student_id: str, org_id: PydanticObjectId, payload: Dict[str, Any]) -> Guardian:
        student = await self._verify_write_permission(student_id, org_id)

        # Enforce max guardians limit (e.g. 5)
        existing = await self.guardian_repo.list_guardians(student.id, org_id)
        if len(existing) >= 5:
            raise GuardianLimitExceeded()

        gua_id = await self._generate_unique_id("GUA", Guardian, "guardianId")
        
        # If this is set as primary, set others as non-primary
        is_primary = payload.get("isPrimary") or payload.get("is_primary") or False
        if is_primary:
            for g in existing:
                if g.is_primary:
                    g.is_primary = False
                    await self.guardian_repo.update(g)

        guardian = Guardian(
            guardianId=gua_id,
            studentId=student.id,
            organizationId=org_id,
            name=payload.get("name"),
            relation=payload.get("relation"),
            phone=payload.get("phone"),
            email=payload.get("email"),
            occupation=payload.get("occupation"),
            address=payload.get("address"),
            isPrimary=is_primary
        )
        return await self.guardian_repo.create(guardian)

    async def update_guardian(self, guardian_id: str, student_id: str, org_id: PydanticObjectId, payload: Dict[str, Any]) -> Guardian:
        student = await self._verify_write_permission(student_id, org_id)
        guardian = await self.guardian_repo.get_by_guardian_id(guardian_id, student.id, org_id)
        if not guardian:
            raise GuardianNotFound()

        is_primary = payload.get("isPrimary") or payload.get("is_primary")
        if is_primary is not None and is_primary != guardian.is_primary:
            if is_primary:
                # Set others to False
                existing = await self.guardian_repo.list_guardians(student.id, org_id)
                for g in existing:
                    if g.is_primary and g.id != guardian.id:
                        g.is_primary = False
                        await self.guardian_repo.update(g)
            guardian.is_primary = is_primary

        if payload.get("name"):
            guardian.name = payload["name"]
        if payload.get("relation"):
            guardian.relation = payload["relation"]
        if payload.get("phone"):
            guardian.phone = payload["phone"]
        if payload.get("email"):
            guardian.email = payload["email"]
        if payload.get("occupation"):
            guardian.occupation = payload["occupation"]
        if payload.get("address"):
            guardian.address = payload["address"]

        return await self.guardian_repo.update(guardian)

    async def delete_guardian(self, guardian_id: str, student_id: str, org_id: PydanticObjectId) -> None:
        student = await self._verify_write_permission(student_id, org_id)
        guardian = await self.guardian_repo.get_by_guardian_id(guardian_id, student.id, org_id)
        if not guardian:
            raise GuardianNotFound()
        
        await guardian.soft_delete()

    # ── Documents ─────────────────────────────────────────────────────────────
    async def add_document(self, student_id: str, org_id: PydanticObjectId, payload: Dict[str, Any]) -> StudentDocument:
        student = await self._verify_write_permission(student_id, org_id)
        doc_id = await self._generate_unique_id("DOC", StudentDocument, "documentId")

        doc = StudentDocument(
            documentId=doc_id,
            studentId=student.id,
            organizationId=org_id,
            name=payload.get("name"),
            filePath=payload.get("filePath") or payload.get("file_path"),
            fileType=payload.get("fileType") or payload.get("file_type") or "PDF",
            fileSize=payload.get("fileSize") or payload.get("file_size") or 0,
            category=DocumentCategory(payload.get("category", DocumentCategory.ACADEMIC)),
            isVerified=False
        )
        return await self.doc_repo.create(doc)

    async def delete_document(self, document_id: str, student_id: str, org_id: PydanticObjectId) -> None:
        student = await self._verify_write_permission(student_id, org_id)
        doc = await self.doc_repo.get_by_document_id(document_id, student.id, org_id)
        if not doc:
            raise DocumentNotFound()
        await doc.soft_delete()

    async def verify_document(self, document_id: str, student_id: str, org_id: PydanticObjectId, verified: bool) -> StudentDocument:
        student = await self._verify_write_permission(student_id, org_id)
        doc = await self.doc_repo.get_by_document_id(document_id, student.id, org_id)
        if not doc:
            raise DocumentNotFound()
        doc.is_verified = verified
        return await doc.save()

    # ── Achievements ──────────────────────────────────────────────────────────
    async def add_achievement(self, student_id: str, org_id: PydanticObjectId, payload: Dict[str, Any]) -> StudentAchievement:
        student = await self._verify_write_permission(student_id, org_id)
        ach_id = await self._generate_unique_id("ACH", StudentAchievement, "achievementId")

        date_val = payload.get("dateEarned") or payload.get("date_earned") or datetime.utcnow()
        if isinstance(date_val, str):
            date_val = datetime.fromisoformat(date_val.replace("Z", ""))

        ach = StudentAchievement(
            achievementId=ach_id,
            studentId=student.id,
            organizationId=org_id,
            title=payload.get("title"),
            description=payload.get("description"),
            dateEarned=date_val,
            category=AchievementCategory(payload.get("category", AchievementCategory.ACADEMIC)),
            certificatePath=payload.get("certificatePath") or payload.get("certificate_path")
        )
        return await self.ach_repo.create(ach)

    async def delete_achievement(self, achievement_id: str, student_id: str, org_id: PydanticObjectId) -> None:
        student = await self._verify_write_permission(student_id, org_id)
        ach = await self.ach_repo.get_by_achievement_id(achievement_id, student.id, org_id)
        if not ach:
            raise AchievementNotFound()
        await ach.soft_delete()

    # ── Skills ────────────────────────────────────────────────────────────────
    async def add_skill(self, student_id: str, org_id: PydanticObjectId, payload: Dict[str, Any]) -> StudentSkill:
        student = await self._verify_write_permission(student_id, org_id)

        # Check unique skill per student
        name = payload.get("name", "").strip()
        existing = await StudentSkill.find_one(
            StudentSkill.student_id == student.id,
            StudentSkill.name == name,
            StudentSkill.is_deleted == False
        )
        if existing:
            # Just update level and save
            existing.level = SkillLevel(payload.get("level", SkillLevel.BEGINNER))
            return await existing.save()

        skl_id = await self._generate_unique_id("SKL", StudentSkill, "skillId")

        skill = StudentSkill(
            skillId=skl_id,
            studentId=student.id,
            organizationId=org_id,
            name=name,
            level=SkillLevel(payload.get("level", SkillLevel.BEGINNER)),
            verified=False
        )
        return await self.skl_repo.create(skill)

    async def delete_skill(self, skill_id: str, student_id: str, org_id: PydanticObjectId) -> None:
        student = await self._verify_write_permission(student_id, org_id)
        skill = await self.skl_repo.get_by_skill_id(skill_id, student.id, org_id)
        if not skill:
            raise SkillNotFound()
        await skill.soft_delete()
