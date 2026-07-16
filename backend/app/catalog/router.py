"""
Catalog Engine — FastAPI Router
================================
17 endpoints for curriculum lifecycle management and subject catalog operations.
All routes are tenant-scoped via /organizations/{org_id}/catalog prefix.
"""
from typing import Optional, List, Any, Dict
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from beanie import PydanticObjectId
from pydantic import BaseModel, Field, ConfigDict

from app.catalog.service import CurriculumService, SubjectService, CatalogService
from app.catalog.exceptions import CatalogException
from app.models.catalog.curriculum import CurriculumStatus
from app.models.catalog.subject import SubjectType, BloomLevel, LearningOutcome, AssessmentScheme, AssessmentComponent
from app.core.identity_context import get_current_user, check_permission
from app.core.logger import logger

router = APIRouter()

# ─────────────────────────────────────────────
# Pydantic Schemas
# ─────────────────────────────────────────────

schema_cfg = ConfigDict(populate_by_name=True, from_attributes=True, use_enum_values=True)


class CurriculumCreateSchema(BaseModel):
    programId: str = Field(..., alias="programId")
    name: str = Field(..., min_length=2, max_length=200)
    effectiveFrom: datetime = Field(default_factory=datetime.utcnow, alias="effectiveFrom")
    description: Optional[str] = Field(default=None, max_length=1000)
    admissionBatch: Optional[str] = Field(default=None, max_length=20, alias="admissionBatch")
    model_config = schema_cfg


class CurriculumUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    effectiveFrom: Optional[datetime] = Field(None, alias="effectiveFrom")
    description: Optional[str] = Field(None, max_length=1000)
    admissionBatch: Optional[str] = Field(None, max_length=20, alias="admissionBatch")
    model_config = schema_cfg


class LearningOutcomeSchema(BaseModel):
    code: str = Field(..., min_length=1, max_length=20)
    description: str = Field(..., min_length=5, max_length=500)
    bloomLevel: BloomLevel = Field(..., alias="bloomLevel")
    model_config = schema_cfg


class AssessmentComponentSchema(BaseModel):
    component: str = Field(..., min_length=1, max_length=100)
    weight: float = Field(..., gt=0.0, le=100.0)
    maxMarks: int = Field(..., ge=1, le=1000, alias="maxMarks")
    model_config = schema_cfg


class AssessmentSchemeSchema(BaseModel):
    components: List[AssessmentComponentSchema] = Field(..., min_length=1)
    passingPercentage: float = Field(..., ge=1.0, le=100.0, alias="passingPercentage")
    model_config = schema_cfg


class SubjectCreateSchema(BaseModel):
    semesterNumber: int = Field(..., ge=1, le=20, alias="semesterNumber")
    subjectCode: str = Field(..., min_length=2, max_length=20, alias="subjectCode")
    name: str = Field(..., min_length=2, max_length=150)
    credits: float = Field(..., ge=0.5, le=30.0)
    subjectType: SubjectType = Field(default=SubjectType.CORE, alias="subjectType")
    isElective: bool = Field(default=False, alias="isElective")
    electiveGroup: Optional[str] = Field(default=None, max_length=100, alias="electiveGroup")
    prerequisites: List[str] = Field(default_factory=list)
    model_config = schema_cfg


class SubjectUpdateSchema(BaseModel):
    semesterNumber: Optional[int] = Field(None, ge=1, le=20, alias="semesterNumber")
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    credits: Optional[float] = Field(None, ge=0.5, le=30.0)
    subjectType: Optional[SubjectType] = Field(None, alias="subjectType")
    isElective: Optional[bool] = Field(None, alias="isElective")
    electiveGroup: Optional[str] = Field(None, max_length=100, alias="electiveGroup")
    prerequisites: Optional[List[str]] = Field(None)
    model_config = schema_cfg


class LearningOutcomesUpdateSchema(BaseModel):
    learningOutcomes: List[LearningOutcomeSchema] = Field(..., alias="learningOutcomes")
    model_config = schema_cfg


def _ok(data: Any, message: str = "Success", meta: dict = {}) -> dict:
    return {"success": True, "message": message, "data": data, "meta": meta, "errors": []}


def _serialize(doc) -> dict:
    """Serialize a Beanie document to a JSON-safe dict."""
    d = doc.model_dump(by_alias=True)
    # Convert ObjectId to string
    for k, v in d.items():
        if hasattr(v, '__str__') and type(v).__name__ in ("PydanticObjectId", "ObjectId"):
            d[k] = str(v)
    if d.get("id"):
        d["id"] = str(d["id"])
    return d


# ─────────────────────────────────────────────
# Curriculum Endpoints
# ─────────────────────────────────────────────

@router.get("/organizations/{org_id}/catalog/curricula", tags=["Catalog Engine"])
async def list_curricula(
    org_id: str,
    programId: Optional[str] = Query(None),
    status: Optional[CurriculumStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    sort_by: str = Query("createdAt"),
    sort_order: str = Query("desc"),
    current_user=Depends(get_current_user),
):
    svc = CurriculumService()
    org_oid = PydanticObjectId(org_id)
    items, total = await svc.list(
        org_oid,
        program_id=programId,
        status=status.value if status else None,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return _ok(
        [_serialize(item) for item in items],
        meta={"total": total, "skip": skip, "limit": limit},
    )


@router.post("/organizations/{org_id}/catalog/curricula", status_code=201, tags=["Catalog Engine"])
async def create_curriculum(
    org_id: str,
    body: CurriculumCreateSchema,
    current_user=Depends(get_current_user),
):
    svc = CurriculumService()
    org_oid = PydanticObjectId(org_id)
    program_oid = PydanticObjectId(body.programId)
    curriculum = await svc.create(
        org_id=org_oid,
        program_id=program_oid,
        name=body.name,
        effective_from=body.effectiveFrom,
        description=body.description,
        admission_batch=body.admissionBatch,
        user_id=str(current_user.id) if current_user else None,
    )
    return _ok(_serialize(curriculum), "Curriculum created successfully.")


@router.get("/organizations/{org_id}/catalog/curricula/{curriculum_id}", tags=["Catalog Engine"])
async def get_curriculum(
    org_id: str,
    curriculum_id: str,
    current_user=Depends(get_current_user),
):
    svc = CurriculumService()
    doc = await svc.get(curriculum_id, PydanticObjectId(org_id))
    return _ok(_serialize(doc))


@router.put("/organizations/{org_id}/catalog/curricula/{curriculum_id}", tags=["Catalog Engine"])
async def update_curriculum(
    org_id: str,
    curriculum_id: str,
    body: CurriculumUpdateSchema,
    current_user=Depends(get_current_user),
):
    svc = CurriculumService()
    update_data = body.model_dump(exclude_none=True, by_alias=True)
    doc = await svc.update(
        curriculum_id,
        PydanticObjectId(org_id),
        update_data,
        user_id=str(current_user.id) if current_user else None,
    )
    return _ok(_serialize(doc), "Curriculum updated.")


@router.delete("/organizations/{org_id}/catalog/curricula/{curriculum_id}", tags=["Catalog Engine"])
async def delete_curriculum(
    org_id: str,
    curriculum_id: str,
    current_user=Depends(get_current_user),
):
    svc = CurriculumService()
    await svc.delete(
        curriculum_id,
        PydanticObjectId(org_id),
        user_id=str(current_user.id) if current_user else None,
    )
    return _ok(None, "Curriculum deleted.")


@router.post(
    "/organizations/{org_id}/catalog/curricula/{curriculum_id}/publish",
    tags=["Catalog Engine"],
)
async def publish_curriculum(
    org_id: str,
    curriculum_id: str,
    current_user=Depends(get_current_user),
):
    svc = CurriculumService()
    doc = await svc.publish(curriculum_id, PydanticObjectId(org_id))
    return _ok(_serialize(doc), "Curriculum published and is now ACTIVE.")


@router.post(
    "/organizations/{org_id}/catalog/curricula/{curriculum_id}/archive",
    tags=["Catalog Engine"],
)
async def archive_curriculum(
    org_id: str,
    curriculum_id: str,
    current_user=Depends(get_current_user),
):
    svc = CurriculumService()
    doc = await svc.archive(curriculum_id, PydanticObjectId(org_id))
    return _ok(_serialize(doc), "Curriculum archived.")


@router.post(
    "/organizations/{org_id}/catalog/curricula/{curriculum_id}/clone",
    status_code=201,
    tags=["Catalog Engine"],
)
async def clone_curriculum(
    org_id: str,
    curriculum_id: str,
    current_user=Depends(get_current_user),
):
    svc = CurriculumService()
    doc = await svc.clone(
        curriculum_id,
        PydanticObjectId(org_id),
        user_id=str(current_user.id) if current_user else None,
    )
    return _ok(_serialize(doc), "Curriculum cloned. A new DRAFT version has been created.")


@router.get(
    "/organizations/{org_id}/catalog/curricula/{curriculum_id}/full",
    tags=["Catalog Engine"],
)
async def get_full_curriculum(
    org_id: str,
    curriculum_id: str,
    current_user=Depends(get_current_user),
):
    svc = CatalogService()
    result = await svc.get_full_curriculum(curriculum_id, PydanticObjectId(org_id))
    return _ok({
        "curriculum": _serialize(result["curriculum"]),
        "semesters": {
            str(sem): [_serialize(s) for s in subjects]
            for sem, subjects in result["semesters"].items()
        },
        "totalSubjects": result["totalSubjects"],
    })


@router.get(
    "/organizations/{org_id}/catalog/curricula/{curriculum_id}/prerequisite-graph",
    tags=["Catalog Engine"],
)
async def get_prerequisite_graph(
    org_id: str,
    curriculum_id: str,
    current_user=Depends(get_current_user),
):
    svc = CatalogService()
    graph = await svc.get_prerequisite_graph(curriculum_id, PydanticObjectId(org_id))
    return _ok(graph)


# ─────────────────────────────────────────────
# Subject Endpoints
# ─────────────────────────────────────────────

@router.get(
    "/organizations/{org_id}/catalog/curricula/{curriculum_id}/subjects",
    tags=["Catalog Engine"],
)
async def list_subjects(
    org_id: str,
    curriculum_id: str,
    semesterNumber: Optional[int] = Query(None, ge=1, le=20),
    subjectType: Optional[SubjectType] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user=Depends(get_current_user),
):
    svc = SubjectService()
    items, total = await svc.list(
        curriculum_id,
        PydanticObjectId(org_id),
        semester_number=semesterNumber,
        subject_type=subjectType.value if subjectType else None,
        skip=skip,
        limit=limit,
    )
    return _ok(
        [_serialize(item) for item in items],
        meta={"total": total, "skip": skip, "limit": limit},
    )


@router.post(
    "/organizations/{org_id}/catalog/curricula/{curriculum_id}/subjects",
    status_code=201,
    tags=["Catalog Engine"],
)
async def create_subject(
    org_id: str,
    curriculum_id: str,
    body: SubjectCreateSchema,
    current_user=Depends(get_current_user),
):
    svc = SubjectService()
    subject = await svc.create(
        org_id=PydanticObjectId(org_id),
        curriculum_id=curriculum_id,
        semester_number=body.semesterNumber,
        subject_code=body.subjectCode,
        name=body.name,
        credits=body.credits,
        subject_type=SubjectType(body.subjectType) if body.subjectType else SubjectType.CORE,
        is_elective=body.isElective,
        elective_group=body.electiveGroup,
        prerequisites=body.prerequisites,
        user_id=str(current_user.id) if current_user else None,
    )
    return _ok(_serialize(subject), "Subject created.")


@router.get(
    "/organizations/{org_id}/catalog/curricula/{curriculum_id}/subjects/{subject_id}",
    tags=["Catalog Engine"],
)
async def get_subject(
    org_id: str,
    curriculum_id: str,
    subject_id: str,
    current_user=Depends(get_current_user),
):
    svc = SubjectService()
    doc = await svc.get(subject_id, curriculum_id, PydanticObjectId(org_id))
    return _ok(_serialize(doc))


@router.put(
    "/organizations/{org_id}/catalog/curricula/{curriculum_id}/subjects/{subject_id}",
    tags=["Catalog Engine"],
)
async def update_subject(
    org_id: str,
    curriculum_id: str,
    subject_id: str,
    body: SubjectUpdateSchema,
    current_user=Depends(get_current_user),
):
    svc = SubjectService()
    update_data = body.model_dump(exclude_none=True, by_alias=True)
    doc = await svc.update(
        subject_id,
        curriculum_id,
        PydanticObjectId(org_id),
        update_data,
        user_id=str(current_user.id) if current_user else None,
    )
    return _ok(_serialize(doc), "Subject updated.")


@router.delete(
    "/organizations/{org_id}/catalog/curricula/{curriculum_id}/subjects/{subject_id}",
    tags=["Catalog Engine"],
)
async def delete_subject(
    org_id: str,
    curriculum_id: str,
    subject_id: str,
    current_user=Depends(get_current_user),
):
    svc = SubjectService()
    await svc.delete(
        subject_id,
        curriculum_id,
        PydanticObjectId(org_id),
        user_id=str(current_user.id) if current_user else None,
    )
    return _ok(None, "Subject deleted.")


@router.put(
    "/organizations/{org_id}/catalog/curricula/{curriculum_id}/subjects/{subject_id}/assessment-scheme",
    tags=["Catalog Engine"],
)
async def update_assessment_scheme(
    org_id: str,
    curriculum_id: str,
    subject_id: str,
    body: AssessmentSchemeSchema,
    current_user=Depends(get_current_user),
):
    svc = SubjectService()
    # Validate weights sum to 100
    total = sum(c.weight for c in body.components)
    if abs(total - 100.0) > 0.01:
        from app.catalog.exceptions import AssessmentSchemeInvalid
        raise AssessmentSchemeInvalid(total)

    scheme = AssessmentScheme(
        components=[
            AssessmentComponent(
                component=c.component,
                weight=c.weight,
                maxMarks=c.maxMarks,
            )
            for c in body.components
        ],
        passingPercentage=body.passingPercentage,
    )
    doc = await svc.update_assessment_scheme(
        subject_id,
        curriculum_id,
        PydanticObjectId(org_id),
        scheme,
        user_id=str(current_user.id) if current_user else None,
    )
    return _ok(_serialize(doc), "Assessment scheme updated.")


@router.put(
    "/organizations/{org_id}/catalog/curricula/{curriculum_id}/subjects/{subject_id}/learning-outcomes",
    tags=["Catalog Engine"],
)
async def update_learning_outcomes(
    org_id: str,
    curriculum_id: str,
    subject_id: str,
    body: LearningOutcomesUpdateSchema,
    current_user=Depends(get_current_user),
):
    svc = SubjectService()
    outcomes = [
        LearningOutcome(
            code=lo.code,
            description=lo.description,
            bloomLevel=lo.bloomLevel,
        )
        for lo in body.learningOutcomes
    ]
    doc = await svc.update_learning_outcomes(
        subject_id,
        curriculum_id,
        PydanticObjectId(org_id),
        outcomes,
        user_id=str(current_user.id) if current_user else None,
    )
    return _ok(_serialize(doc), "Learning outcomes updated.")
