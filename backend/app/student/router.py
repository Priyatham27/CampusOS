from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, Body, status, Request
from beanie import PydanticObjectId

from app.schemas.schemas import APIResponse
from app.core.identity_context import check_permission, get_current_identity
from app.student.models import Student, Guardian, StudentDocument, StudentAchievement, StudentSkill
from app.student.service import StudentService, ProfileService
from app.student.schemas import (
    StudentCreateSchema, StudentUpdateSchema, StudentResponseSchema,
    GuardianCreateUpdateSchema, GuardianResponseSchema,
    DocumentCreateSchema, DocumentResponseSchema,
    AchievementCreateSchema, AchievementResponseSchema,
    SkillCreateSchema, SkillResponseSchema,
    StudentNoteCreateSchema, StudentNoteResponseSchema,
    BulkImportSchema, EmergencyContactSchema, StudentPreferenceSchema
)
from app.student.exceptions import StudentException

router = APIRouter()

def get_student_service() -> StudentService:
    return StudentService()

def get_profile_service() -> ProfileService:
    return ProfileService()

def map_student_response(s: Student) -> StudentResponseSchema:
    return StudentResponseSchema(
        id=str(s.id),
        studentId=s.student_id,
        userId=str(s.user_id),
        organizationId=str(s.organization_id),
        rollNumber=s.roll_number,
        firstName=s.first_name,
        lastName=s.last_name,
        email=s.email,
        phone=s.phone,
        dateOfBirth=s.date_of_birth,
        gender=s.gender,
        bloodGroup=s.blood_group,
        admissionDate=s.admission_date,
        status=s.status,
        isArchived=s.is_archived,
        academicYearId=str(s.academic_year_id) if s.academic_year_id else None,
        departmentId=str(s.department_id) if s.department_id else None,
        programId=str(s.program_id) if s.program_id else None,
        branchId=str(s.branch_id) if s.branch_id else None,
        semesterId=str(s.semester_id) if s.semester_id else None,
        sectionId=str(s.section_id) if s.section_id else None,
        emergencyContact=EmergencyContactSchema(
            name=s.emergency_contact.name,
            relation=s.emergency_contact.relation,
            phone=s.emergency_contact.phone,
            alternativePhone=s.emergency_contact.alternative_phone,
            email=s.emergency_contact.email
        ) if s.emergency_contact else None,
        preferences=StudentPreferenceSchema(
            notificationsEnabled=s.preferences.notifications_enabled,
            theme=s.preferences.theme,
            language=s.preferences.language
        ),
        tags=s.tags,
        notes=[
            StudentNoteResponseSchema(
                noteId=n.note_id,
                author=n.author,
                content=n.content,
                createdAt=n.created_at
            ) for n in s.notes
        ]
    )

def map_guardian_response(g: Guardian) -> GuardianResponseSchema:
    return GuardianResponseSchema(
        id=str(g.id),
        guardianId=g.guardian_id,
        studentId=str(g.student_id),
        organizationId=str(g.organization_id),
        name=g.name,
        relation=g.relation,
        phone=g.phone,
        email=g.email,
        occupation=g.occupation,
        address=g.address,
        isPrimary=g.is_primary
    )

def map_doc_response(d: StudentDocument) -> DocumentResponseSchema:
    return DocumentResponseSchema(
        id=str(d.id),
        documentId=d.document_id,
        studentId=str(d.student_id),
        organizationId=str(d.organization_id),
        name=d.name,
        filePath=d.file_path,
        fileType=d.file_type,
        fileSize=d.file_size,
        uploadedAt=d.uploaded_at,
        category=d.category,
        isVerified=d.is_verified
    )

def map_ach_response(a: StudentAchievement) -> AchievementResponseSchema:
    return AchievementResponseSchema(
        id=str(a.id),
        achievementId=a.achievement_id,
        studentId=str(a.student_id),
        organizationId=str(a.organization_id),
        title=a.title,
        description=a.description,
        dateEarned=a.date_earned,
        category=a.category,
        certificatePath=a.certificate_path
    )

def map_skill_response(k: StudentSkill) -> SkillResponseSchema:
    return SkillResponseSchema(
        id=str(k.id),
        skillId=k.skill_id,
        studentId=str(k.student_id),
        organizationId=str(k.organization_id),
        name=k.name,
        level=k.level,
        verified=k.verified
    )

# ── Primary Student CRUD ──────────────────────────────────────────────────
@router.get(
    "/organizations/{organizationId}/students",
    dependencies=[Depends(check_permission("student:read"))],
    response_model=APIResponse
)
async def search_students(
    organizationId: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None),
    academicYearId: Optional[str] = Query(None),
    semesterId: Optional[str] = Query(None),
    branchId: Optional[str] = Query(None),
    searchQuery: Optional[str] = Query(None),
    student_svc: StudentService = Depends(get_student_service)
):
    org_id = PydanticObjectId(organizationId)
    filters = {
        "status": status,
        "academic_year_id": academicYearId,
        "semester_id": semesterId,
        "branch_id": branchId,
        "search_query": searchQuery
    }
    
    results, total = await student_svc.student_repo.list_students(org_id, skip, limit, filters)
    data_list = [map_student_response(s) for s in results]
    
    return APIResponse(
        success=True,
        message="Students list retrieved.",
        data=data_list,
        meta={"total": total, "skip": skip, "limit": limit}
    )

@router.post(
    "/organizations/{organizationId}/students",
    dependencies=[Depends(check_permission("student:write"))],
    response_model=APIResponse
)
async def create_student(
    organizationId: str,
    payload: StudentCreateSchema,
    student_svc: StudentService = Depends(get_student_service)
):
    org_id = PydanticObjectId(organizationId)
    # Parse payload dates
    from datetime import datetime
    try:
        dob_parsed = datetime.fromisoformat(payload.date_of_birth.replace("Z", ""))
    except Exception:
        dob_parsed = datetime.strptime(payload.date_of_birth, "%Y-%m-%d")

    raw_payload = payload.model_dump()
    raw_payload["dateOfBirth"] = dob_parsed

    student = await student_svc.create_student(org_id, raw_payload)
    return APIResponse(
        success=True,
        message="Student profile created successfully.",
        data=map_student_response(student)
    )

@router.put(
    "/organizations/{organizationId}/students/{studentId}",
    dependencies=[Depends(check_permission("student:write"))],
    response_model=APIResponse
)
async def update_student(
    organizationId: str,
    studentId: str,
    payload: StudentUpdateSchema,
    student_svc: StudentService = Depends(get_student_service)
):
    org_id = PydanticObjectId(organizationId)
    raw_payload = payload.model_dump(exclude_unset=True)
    if payload.date_of_birth:
        from datetime import datetime
        try:
            raw_payload["dateOfBirth"] = datetime.fromisoformat(payload.date_of_birth.replace("Z", ""))
        except Exception:
            raw_payload["dateOfBirth"] = datetime.strptime(payload.date_of_birth, "%Y-%m-%d")

    student = await student_svc.update_student(studentId, org_id, raw_payload)
    return APIResponse(
        success=True,
        message="Student profile updated successfully.",
        data=map_student_response(student)
    )

@router.post(
    "/organizations/{organizationId}/students/{studentId}/archive",
    dependencies=[Depends(check_permission("student:write"))],
    response_model=APIResponse
)
async def archive_student(
    organizationId: str,
    studentId: str,
    student_svc: StudentService = Depends(get_student_service)
):
    org_id = PydanticObjectId(organizationId)
    student = await student_svc.archive_student(studentId, org_id)
    return APIResponse(
        success=True,
        message="Student profile archived.",
        data=map_student_response(student)
    )

@router.post(
    "/organizations/{organizationId}/students/{studentId}/restore",
    dependencies=[Depends(check_permission("student:write"))],
    response_model=APIResponse
)
async def restore_student(
    organizationId: str,
    studentId: str,
    student_svc: StudentService = Depends(get_student_service)
):
    org_id = PydanticObjectId(organizationId)
    student = await student_svc.restore_student(studentId, org_id)
    return APIResponse(
        success=True,
        message="Student profile restored to active status.",
        data=map_student_response(student)
    )

# ── Consolidated Profile Data ─────────────────────────────────────────────
@router.get(
    "/organizations/{organizationId}/students/{studentId}/profile",
    dependencies=[Depends(check_permission("student:read"))],
    response_model=APIResponse
)
async def get_student_profile(
    organizationId: str,
    studentId: str,
    student_svc: StudentService = Depends(get_student_service),
    profile_svc: ProfileService = Depends(get_profile_service)
):
    org_id = PydanticObjectId(organizationId)
    student = await student_svc.student_repo.get_by_student_id(studentId, org_id)
    if not student:
        raise StudentNotFound()

    guardians = await profile_svc.guardian_repo.list_guardians(student.id, org_id)
    documents = await profile_svc.doc_repo.list_documents(student.id, org_id)
    achievements = await profile_svc.ach_repo.list_achievements(student.id, org_id)
    skills = await profile_svc.skl_repo.list_skills(student.id, org_id)

    profile_data = {
        "student": map_student_response(student),
        "guardians": [map_guardian_response(g) for g in guardians],
        "documents": [map_doc_response(d) for d in documents],
        "achievements": [map_ach_response(a) for a in achievements],
        "skills": [map_skill_response(k) for k in skills]
    }
    return APIResponse(
        success=True,
        message="Consolidated student profile fetched successfully.",
        data=profile_data
    )

# ── Bulk Import / Export ──────────────────────────────────────────────────
@router.post(
    "/organizations/{organizationId}/students/import",
    dependencies=[Depends(check_permission("student:write"))],
    response_model=APIResponse
)
async def import_students(
    organizationId: str,
    payload: BulkImportSchema,
    student_svc: StudentService = Depends(get_student_service)
):
    org_id = PydanticObjectId(organizationId)
    raw_records = [r.model_dump() for r in payload.records]
    results = await student_svc.bulk_import_students(org_id, raw_records)
    return APIResponse(
        success=True,
        message="Bulk student import execution completed.",
        data=results
    )

# ── Guardians nested endpoints ────────────────────────────────────────────
@router.post(
    "/organizations/{organizationId}/students/{studentId}/guardians",
    dependencies=[Depends(check_permission("student:write"))],
    response_model=APIResponse
)
async def add_student_guardian(
    organizationId: str,
    studentId: str,
    payload: GuardianCreateUpdateSchema,
    profile_svc: ProfileService = Depends(get_profile_service)
):
    org_id = PydanticObjectId(organizationId)
    guardian = await profile_svc.add_guardian(studentId, org_id, payload.model_dump())
    return APIResponse(
        success=True,
        message="Guardian added.",
        data=map_guardian_response(guardian)
    )

@router.put(
    "/organizations/{organizationId}/students/{studentId}/guardians/{guardianId}",
    dependencies=[Depends(check_permission("student:write"))],
    response_model=APIResponse
)
async def update_student_guardian(
    organizationId: str,
    studentId: str,
    guardianId: str,
    payload: GuardianCreateUpdateSchema,
    profile_svc: ProfileService = Depends(get_profile_service)
):
    org_id = PydanticObjectId(organizationId)
    guardian = await profile_svc.update_guardian(guardianId, studentId, org_id, payload.model_dump())
    return APIResponse(
        success=True,
        message="Guardian updated.",
        data=map_guardian_response(guardian)
    )

@router.delete(
    "/organizations/{organizationId}/students/{studentId}/guardians/{guardianId}",
    dependencies=[Depends(check_permission("student:write"))],
    response_model=APIResponse
)
async def delete_student_guardian(
    organizationId: str,
    studentId: str,
    guardianId: str,
    profile_svc: ProfileService = Depends(get_profile_service)
):
    org_id = PydanticObjectId(organizationId)
    await profile_svc.delete_guardian(guardianId, studentId, org_id)
    return APIResponse(
        success=True,
        message="Guardian deleted.",
        data=None
    )

# ── Documents nested endpoints ────────────────────────────────────────────
@router.post(
    "/organizations/{organizationId}/students/{studentId}/documents",
    dependencies=[Depends(check_permission("student:write"))],
    response_model=APIResponse
)
async def add_student_document(
    organizationId: str,
    studentId: str,
    payload: DocumentCreateSchema,
    profile_svc: ProfileService = Depends(get_profile_service)
):
    org_id = PydanticObjectId(organizationId)
    doc = await profile_svc.add_document(studentId, org_id, payload.model_dump())
    return APIResponse(
        success=True,
        message="Student document registered.",
        data=map_doc_response(doc)
    )

@router.delete(
    "/organizations/{organizationId}/students/{studentId}/documents/{documentId}",
    dependencies=[Depends(check_permission("student:write"))],
    response_model=APIResponse
)
async def delete_student_document(
    organizationId: str,
    studentId: str,
    documentId: str,
    profile_svc: ProfileService = Depends(get_profile_service)
):
    org_id = PydanticObjectId(organizationId)
    await profile_svc.delete_document(documentId, studentId, org_id)
    return APIResponse(
        success=True,
        message="Document record removed.",
        data=None
    )

@router.post(
    "/organizations/{organizationId}/students/{studentId}/documents/{documentId}/verify",
    dependencies=[Depends(check_permission("student:write"))],
    response_model=APIResponse
)
async def verify_student_document(
    organizationId: str,
    studentId: str,
    documentId: str,
    verified: bool = Query(...),
    profile_svc: ProfileService = Depends(get_profile_service)
):
    org_id = PydanticObjectId(organizationId)
    doc = await profile_svc.verify_document(documentId, studentId, org_id, verified)
    return APIResponse(
        success=True,
        message="Document verification status updated.",
        data=map_doc_response(doc)
    )

# ── Achievements nested endpoints ─────────────────────────────────────────
@router.post(
    "/organizations/{organizationId}/students/{studentId}/achievements",
    dependencies=[Depends(check_permission("student:write"))],
    response_model=APIResponse
)
async def add_student_achievement(
    organizationId: str,
    studentId: str,
    payload: AchievementCreateSchema,
    profile_svc: ProfileService = Depends(get_profile_service)
):
    org_id = PydanticObjectId(organizationId)
    ach = await profile_svc.add_achievement(studentId, org_id, payload.model_dump())
    return APIResponse(
        success=True,
        message="Achievement logged.",
        data=map_ach_response(ach)
    )

@router.delete(
    "/organizations/{organizationId}/students/{studentId}/achievements/{achievementId}",
    dependencies=[Depends(check_permission("student:write"))],
    response_model=APIResponse
)
async def delete_student_achievement(
    organizationId: str,
    studentId: str,
    achievementId: str,
    profile_svc: ProfileService = Depends(get_profile_service)
):
    org_id = PydanticObjectId(organizationId)
    await profile_svc.delete_achievement(achievementId, studentId, org_id)
    return APIResponse(
        success=True,
        message="Achievement removed.",
        data=None
    )

# ── Skills nested endpoints ───────────────────────────────────────────────
@router.post(
    "/organizations/{organizationId}/students/{studentId}/skills",
    dependencies=[Depends(check_permission("student:write"))],
    response_model=APIResponse
)
async def add_student_skill(
    organizationId: str,
    studentId: str,
    payload: SkillCreateSchema,
    profile_svc: ProfileService = Depends(get_profile_service)
):
    org_id = PydanticObjectId(organizationId)
    skill = await profile_svc.add_skill(studentId, org_id, payload.model_dump())
    return APIResponse(
        success=True,
        message="Skill badge registered.",
        data=map_skill_response(skill)
    )

@router.delete(
    "/organizations/{organizationId}/students/{studentId}/skills/{skillId}",
    dependencies=[Depends(check_permission("student:write"))],
    response_model=APIResponse
)
async def delete_student_skill(
    organizationId: str,
    studentId: str,
    skillId: str,
    profile_svc: ProfileService = Depends(get_profile_service)
):
    org_id = PydanticObjectId(organizationId)
    await profile_svc.delete_skill(skillId, studentId, org_id)
    return APIResponse(
        success=True,
        message="Skill badge removed.",
        data=None
    )

# ── Student Notes ─────────────────────────────────────────────────────────
@router.post(
    "/organizations/{organizationId}/students/{studentId}/notes",
    dependencies=[Depends(check_permission("student:write"))],
    response_model=APIResponse
)
async def add_student_note(
    organizationId: str,
    studentId: str,
    payload: StudentNoteCreateSchema,
    request: Request,
    student_svc: StudentService = Depends(get_student_service)
):
    org_id = PydanticObjectId(organizationId)
    author = "System Admin"
    try:
        identity = request.state.identity_context
        if identity and identity.user:
            author = f"{identity.user.username}"
    except Exception:
        pass
    
    student = await student_svc.add_note(studentId, org_id, author, payload.content)
    return APIResponse(
        success=True,
        message="Note logged.",
        data=map_student_response(student)
    )
