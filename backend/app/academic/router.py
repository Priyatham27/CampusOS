"""
Academic Platform API Router
==============================
Full CRUD + Bulk operations for all Academic domain entities.
All write operations are protected with RBAC permission guards.
All read operations require a valid identity context (org isolation).

Endpoints follow the pattern:
    /organizations/{organizationId}/academic-years
    /organizations/{organizationId}/departments
    /organizations/{organizationId}/programs
    /organizations/{organizationId}/branches
    /organizations/{organizationId}/semesters
    /organizations/{organizationId}/sections
    /organizations/{organizationId}/courses
"""
from datetime import datetime
from typing import List, Optional, Any

from fastapi import APIRouter, Depends, Query, Body, Request, status

from app.schemas.schemas import APIResponse
from app.schemas.academic_schemas import (
    AcademicYearCreateSchema, AcademicYearUpdateSchema, AcademicYearResponseSchema,
    AcademicYearBulkUpdateSchema,
    DepartmentCreateSchema, DepartmentUpdateSchema, DepartmentResponseSchema,
    DepartmentBulkUpdateSchema,
    ProgramCreateSchema, ProgramUpdateSchema, ProgramResponseSchema,
    ProgramBulkUpdateSchema,
    BranchCreateSchema, BranchUpdateSchema, BranchResponseSchema,
    BranchBulkUpdateSchema,
    SemesterCreateSchema, SemesterUpdateSchema, SemesterResponseSchema,
    SectionCreateSchema, SectionUpdateSchema, SectionResponseSchema,
    SectionBulkUpdateSchema,
    CourseCreateSchema, CourseUpdateSchema, CourseResponseSchema,
    CourseBulkUpdateSchema,
    BulkDeletePayload,
)
from app.academic.service import AcademicService
from app.core.identity_context import check_permission, get_current_identity
from app.core.database import get_db

router = APIRouter()


def get_academic_service() -> AcademicService:
    return AcademicService()


async def _audit(org_id: Any, action: str, details: dict) -> None:
    """Write an audit log entry to MongoDB."""
    try:
        db = get_db()
        await db["audit_logs"].insert_one({
            "organizationId": org_id,
            "action": action,
            "timestamp": datetime.utcnow(),
            "performedBy": "system",
            "module": "academic",
            "details": details,
        })
    except Exception:
        pass  # Audit failure must never break the primary operation


# ============================================================================
# ACADEMIC YEARS
# ============================================================================

@router.post(
    "/organizations/{organizationId}/academic-years",
    response_model=APIResponse[AcademicYearResponseSchema],
    summary="Create Academic Year",
    tags=["Academic Platform"],
)
async def create_academic_year(
    organizationId: str,
    payload: AcademicYearCreateSchema,
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:write")),
):
    res = await service.create_academic_year(organizationId, payload.model_dump(by_alias=True))
    await _audit(res.organization_id, "academic_year.created", {"id": res.academic_year_id, "name": res.name})
    return APIResponse(success=True, message="Academic Year created successfully.", data=res)


@router.get(
    "/organizations/{organizationId}/academic-years",
    response_model=APIResponse[List[AcademicYearResponseSchema]],
    summary="List Academic Years",
    tags=["Academic Platform"],
)
async def list_academic_years(
    organizationId: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    sortBy: str = Query("createdAt"),
    sortOrder: str = Query("asc"),
    current: Optional[bool] = Query(None),
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(get_current_identity),
):
    filters = {}
    if current is not None:
        filters["current"] = current
    items, total = await service.list_academic_years(organizationId, skip, limit, sortBy, sortOrder, filters)
    return APIResponse(success=True, data=items, meta={"pagination": {"skip": skip, "limit": limit, "total": total}})


@router.post(
    "/organizations/{organizationId}/academic-years/bulk",
    response_model=APIResponse[List[AcademicYearResponseSchema]],
    summary="Bulk Create Academic Years",
    tags=["Academic Platform"],
)
async def bulk_create_academic_years(
    organizationId: str,
    payload: List[AcademicYearCreateSchema] = Body(...),
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:write")),
):
    items = [p.model_dump(by_alias=True) for p in payload]
    res = await service.bulk_create_academic_years(organizationId, items)
    if res:
        await _audit(res[0].organization_id, "academic_year.bulk_created", {"count": len(res)})
    return APIResponse(success=True, message=f"Bulk created {len(res)} Academic Years.", data=res)


@router.patch(
    "/organizations/{organizationId}/academic-years/bulk",
    response_model=APIResponse[bool],
    summary="Bulk Update Academic Years",
    tags=["Academic Platform"],
)
async def bulk_update_academic_years(
    organizationId: str,
    payload: List[AcademicYearBulkUpdateSchema] = Body(...),
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:write")),
):
    items = [p.model_dump(exclude_unset=True, by_alias=True) for p in payload]
    await service.bulk_update_academic_years(organizationId, items)
    return APIResponse(success=True, message=f"Bulk updated {len(payload)} Academic Years.", data=True)


@router.delete(
    "/organizations/{organizationId}/academic-years/bulk",
    response_model=APIResponse[bool],
    summary="Bulk Delete Academic Years",
    tags=["Academic Platform"],
)
async def bulk_delete_academic_years(
    organizationId: str,
    payload: BulkDeletePayload = Body(...),
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:delete")),
):
    await service.bulk_delete_academic_years(organizationId, payload.ids)
    return APIResponse(success=True, message=f"Bulk deleted {len(payload.ids)} Academic Years.", data=True)


@router.get(
    "/organizations/{organizationId}/academic-years/{id}",
    response_model=APIResponse[AcademicYearResponseSchema],
    summary="Get Academic Year by ID",
    tags=["Academic Platform"],
)
async def get_academic_year(
    organizationId: str,
    id: str,
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(get_current_identity),
):
    res = await service.get_academic_year(organizationId, id)
    return APIResponse(success=True, data=res)


@router.patch(
    "/organizations/{organizationId}/academic-years/{id}",
    response_model=APIResponse[AcademicYearResponseSchema],
    summary="Update Academic Year",
    tags=["Academic Platform"],
)
async def update_academic_year(
    organizationId: str,
    id: str,
    payload: AcademicYearUpdateSchema,
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:write")),
):
    res = await service.update_academic_year(organizationId, id, payload.model_dump(exclude_unset=True))
    await _audit(res.organization_id, "academic_year.updated", {"id": id})
    return APIResponse(success=True, message="Academic Year updated successfully.", data=res)


@router.delete(
    "/organizations/{organizationId}/academic-years/{id}",
    response_model=APIResponse[bool],
    summary="Delete Academic Year",
    tags=["Academic Platform"],
)
async def delete_academic_year(
    organizationId: str,
    id: str,
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:delete")),
):
    res = await service.get_academic_year(organizationId, id)
    await service.delete_academic_year(organizationId, id)
    await _audit(res.organization_id, "academic_year.deleted", {"id": id})
    return APIResponse(success=True, message="Academic Year soft deleted.", data=True)


# ============================================================================
# DEPARTMENTS
# ============================================================================

@router.post(
    "/organizations/{organizationId}/departments",
    response_model=APIResponse[DepartmentResponseSchema],
    summary="Create Department",
    tags=["Academic Platform"],
)
async def create_department(
    organizationId: str,
    payload: DepartmentCreateSchema,
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("department:write")),
):
    res = await service.create_department(organizationId, payload.model_dump())
    await _audit(res.organization_id, "department.created", {"id": res.department_id, "code": res.code})
    return APIResponse(success=True, message="Department created successfully.", data=res)


@router.get(
    "/organizations/{organizationId}/departments",
    response_model=APIResponse[List[DepartmentResponseSchema]],
    summary="List Departments",
    tags=["Academic Platform"],
)
async def list_departments(
    organizationId: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    sortBy: str = Query("createdAt"),
    sortOrder: str = Query("asc"),
    status: Optional[str] = Query(None),
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(get_current_identity),
):
    filters = {}
    if status:
        filters["status"] = status
    items, total = await service.list_departments(organizationId, skip, limit, sortBy, sortOrder, filters)
    return APIResponse(success=True, data=items, meta={"pagination": {"skip": skip, "limit": limit, "total": total}})


@router.post(
    "/organizations/{organizationId}/departments/bulk",
    response_model=APIResponse[List[DepartmentResponseSchema]],
    summary="Bulk Create Departments",
    tags=["Academic Platform"],
)
async def bulk_create_departments(
    organizationId: str,
    payload: List[DepartmentCreateSchema] = Body(...),
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("department:write")),
):
    items = [p.model_dump() for p in payload]
    res = await service.bulk_create_departments(organizationId, items)
    if res:
        await _audit(res[0].organization_id, "department.bulk_created", {"count": len(res)})
    return APIResponse(success=True, message=f"Bulk created {len(res)} Departments.", data=res)


@router.patch(
    "/organizations/{organizationId}/departments/bulk",
    response_model=APIResponse[bool],
    summary="Bulk Update Departments",
    tags=["Academic Platform"],
)
async def bulk_update_departments(
    organizationId: str,
    payload: List[DepartmentBulkUpdateSchema] = Body(...),
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("department:write")),
):
    items = [p.model_dump(exclude_unset=True, by_alias=True) for p in payload]
    await service.bulk_update_departments(organizationId, items)
    return APIResponse(success=True, message=f"Bulk updated {len(payload)} Departments.", data=True)


@router.delete(
    "/organizations/{organizationId}/departments/bulk",
    response_model=APIResponse[bool],
    summary="Bulk Delete Departments",
    tags=["Academic Platform"],
)
async def bulk_delete_departments(
    organizationId: str,
    payload: BulkDeletePayload = Body(...),
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("department:delete")),
):
    await service.bulk_delete_departments(organizationId, payload.ids)
    return APIResponse(success=True, message=f"Bulk deleted {len(payload.ids)} Departments.", data=True)


@router.get(
    "/organizations/{organizationId}/departments/{id}",
    response_model=APIResponse[DepartmentResponseSchema],
    summary="Get Department by ID",
    tags=["Academic Platform"],
)
async def get_department(
    organizationId: str,
    id: str,
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(get_current_identity),
):
    res = await service.get_department(organizationId, id)
    return APIResponse(success=True, data=res)


@router.patch(
    "/organizations/{organizationId}/departments/{id}",
    response_model=APIResponse[DepartmentResponseSchema],
    summary="Update Department",
    tags=["Academic Platform"],
)
async def update_department(
    organizationId: str,
    id: str,
    payload: DepartmentUpdateSchema,
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("department:write")),
):
    res = await service.update_department(organizationId, id, payload.model_dump(exclude_unset=True))
    await _audit(res.organization_id, "department.updated", {"id": id})
    return APIResponse(success=True, message="Department updated successfully.", data=res)


@router.delete(
    "/organizations/{organizationId}/departments/{id}",
    response_model=APIResponse[bool],
    summary="Delete Department",
    tags=["Academic Platform"],
)
async def delete_department(
    organizationId: str,
    id: str,
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("department:delete")),
):
    res = await service.get_department(organizationId, id)
    await service.delete_department(organizationId, id)
    await _audit(res.organization_id, "department.deleted", {"id": id})
    return APIResponse(success=True, message="Department soft deleted.", data=True)


# ============================================================================
# PROGRAMS
# ============================================================================

@router.post(
    "/organizations/{organizationId}/programs",
    response_model=APIResponse[ProgramResponseSchema],
    summary="Create Program",
    tags=["Academic Platform"],
)
async def create_program(
    organizationId: str,
    payload: ProgramCreateSchema,
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:write")),
):
    res = await service.create_program(organizationId, payload.model_dump(by_alias=True))
    await _audit(res.organization_id, "program.created", {"id": res.program_id})
    return APIResponse(success=True, message="Program created successfully.", data=res)


@router.get(
    "/organizations/{organizationId}/programs",
    response_model=APIResponse[List[ProgramResponseSchema]],
    summary="List Programs",
    tags=["Academic Platform"],
)
async def list_programs(
    organizationId: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    sortBy: str = Query("createdAt"),
    sortOrder: str = Query("asc"),
    departmentId: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(get_current_identity),
):
    filters = {}
    if departmentId:
        filters["departmentId"] = departmentId
    if level:
        filters["level"] = level
    items, total = await service.list_programs(organizationId, skip, limit, sortBy, sortOrder, filters)
    return APIResponse(success=True, data=items, meta={"pagination": {"skip": skip, "limit": limit, "total": total}})


@router.post(
    "/organizations/{organizationId}/programs/bulk",
    response_model=APIResponse[List[ProgramResponseSchema]],
    summary="Bulk Create Programs",
    tags=["Academic Platform"],
)
async def bulk_create_programs(
    organizationId: str,
    payload: List[ProgramCreateSchema] = Body(...),
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:write")),
):
    items = [p.model_dump(by_alias=True) for p in payload]
    res = await service.bulk_create_programs(organizationId, items)
    return APIResponse(success=True, message=f"Bulk created {len(res)} Programs.", data=res)


@router.patch(
    "/organizations/{organizationId}/programs/bulk",
    response_model=APIResponse[bool],
    summary="Bulk Update Programs",
    tags=["Academic Platform"],
)
async def bulk_update_programs(
    organizationId: str,
    payload: List[ProgramBulkUpdateSchema] = Body(...),
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:write")),
):
    items = [p.model_dump(exclude_unset=True, by_alias=True) for p in payload]
    await service.bulk_update_programs(organizationId, items)
    return APIResponse(success=True, message=f"Bulk updated {len(payload)} Programs.", data=True)


@router.delete(
    "/organizations/{organizationId}/programs/bulk",
    response_model=APIResponse[bool],
    summary="Bulk Delete Programs",
    tags=["Academic Platform"],
)
async def bulk_delete_programs(
    organizationId: str,
    payload: BulkDeletePayload = Body(...),
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:write")),
):
    await service.bulk_delete_programs(organizationId, payload.ids)
    return APIResponse(success=True, message=f"Bulk deleted {len(payload.ids)} Programs.", data=True)


@router.get(
    "/organizations/{organizationId}/programs/{id}",
    response_model=APIResponse[ProgramResponseSchema],
    summary="Get Program by ID",
    tags=["Academic Platform"],
)
async def get_program(
    organizationId: str,
    id: str,
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(get_current_identity),
):
    res = await service.get_program(organizationId, id)
    return APIResponse(success=True, data=res)


@router.patch(
    "/organizations/{organizationId}/programs/{id}",
    response_model=APIResponse[ProgramResponseSchema],
    summary="Update Program",
    tags=["Academic Platform"],
)
async def update_program(
    organizationId: str,
    id: str,
    payload: ProgramUpdateSchema,
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:write")),
):
    res = await service.update_program(organizationId, id, payload.model_dump(exclude_unset=True, by_alias=True))
    await _audit(res.organization_id, "program.updated", {"id": id})
    return APIResponse(success=True, message="Program updated successfully.", data=res)


@router.delete(
    "/organizations/{organizationId}/programs/{id}",
    response_model=APIResponse[bool],
    summary="Delete Program",
    tags=["Academic Platform"],
)
async def delete_program(
    organizationId: str,
    id: str,
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:write")),
):
    res = await service.get_program(organizationId, id)
    await service.delete_program(organizationId, id)
    await _audit(res.organization_id, "program.deleted", {"id": id})
    return APIResponse(success=True, message="Program soft deleted.", data=True)


# ============================================================================
# BRANCHES
# ============================================================================

@router.post(
    "/organizations/{organizationId}/branches",
    response_model=APIResponse[BranchResponseSchema],
    summary="Create Branch",
    tags=["Academic Platform"],
)
async def create_branch(
    organizationId: str,
    payload: BranchCreateSchema,
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:write")),
):
    res = await service.create_branch(organizationId, payload.model_dump(by_alias=True))
    await _audit(res.organization_id, "branch.created", {"id": res.branch_id, "code": res.code})
    return APIResponse(success=True, message="Branch created successfully.", data=res)


@router.get(
    "/organizations/{organizationId}/branches",
    response_model=APIResponse[List[BranchResponseSchema]],
    summary="List Branches",
    tags=["Academic Platform"],
)
async def list_branches(
    organizationId: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    sortBy: str = Query("createdAt"),
    sortOrder: str = Query("asc"),
    departmentId: Optional[str] = Query(None),
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(get_current_identity),
):
    filters = {}
    if departmentId:
        filters["departmentId"] = departmentId
    items, total = await service.list_branches(organizationId, skip, limit, sortBy, sortOrder, filters)
    return APIResponse(success=True, data=items, meta={"pagination": {"skip": skip, "limit": limit, "total": total}})


@router.post(
    "/organizations/{organizationId}/branches/bulk",
    response_model=APIResponse[List[BranchResponseSchema]],
    summary="Bulk Create Branches",
    tags=["Academic Platform"],
)
async def bulk_create_branches(
    organizationId: str,
    payload: List[BranchCreateSchema] = Body(...),
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:write")),
):
    items = [p.model_dump(by_alias=True) for p in payload]
    res = await service.bulk_create_branches(organizationId, items)
    return APIResponse(success=True, message=f"Bulk created {len(res)} Branches.", data=res)


@router.patch(
    "/organizations/{organizationId}/branches/bulk",
    response_model=APIResponse[bool],
    summary="Bulk Update Branches",
    tags=["Academic Platform"],
)
async def bulk_update_branches(
    organizationId: str,
    payload: List[BranchBulkUpdateSchema] = Body(...),
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:write")),
):
    items = [p.model_dump(exclude_unset=True, by_alias=True) for p in payload]
    await service.bulk_update_branches(organizationId, items)
    return APIResponse(success=True, message=f"Bulk updated {len(payload)} Branches.", data=True)


@router.delete(
    "/organizations/{organizationId}/branches/bulk",
    response_model=APIResponse[bool],
    summary="Bulk Delete Branches",
    tags=["Academic Platform"],
)
async def bulk_delete_branches(
    organizationId: str,
    payload: BulkDeletePayload = Body(...),
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:write")),
):
    await service.bulk_delete_branches(organizationId, payload.ids)
    return APIResponse(success=True, message=f"Bulk deleted {len(payload.ids)} Branches.", data=True)


@router.get(
    "/organizations/{organizationId}/branches/{id}",
    response_model=APIResponse[BranchResponseSchema],
    summary="Get Branch by ID",
    tags=["Academic Platform"],
)
async def get_branch(
    organizationId: str,
    id: str,
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(get_current_identity),
):
    res = await service.get_branch(organizationId, id)
    return APIResponse(success=True, data=res)


@router.patch(
    "/organizations/{organizationId}/branches/{id}",
    response_model=APIResponse[BranchResponseSchema],
    summary="Update Branch",
    tags=["Academic Platform"],
)
async def update_branch(
    organizationId: str,
    id: str,
    payload: BranchUpdateSchema,
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:write")),
):
    res = await service.update_branch(organizationId, id, payload.model_dump(exclude_unset=True, by_alias=True))
    await _audit(res.organization_id, "branch.updated", {"id": id})
    return APIResponse(success=True, message="Branch updated successfully.", data=res)


@router.delete(
    "/organizations/{organizationId}/branches/{id}",
    response_model=APIResponse[bool],
    summary="Delete Branch",
    tags=["Academic Platform"],
)
async def delete_branch(
    organizationId: str,
    id: str,
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:write")),
):
    res = await service.get_branch(organizationId, id)
    await service.delete_branch(organizationId, id)
    await _audit(res.organization_id, "branch.deleted", {"id": id})
    return APIResponse(success=True, message="Branch soft deleted.", data=True)


# ============================================================================
# SEMESTERS
# ============================================================================

@router.post(
    "/organizations/{organizationId}/semesters",
    response_model=APIResponse[SemesterResponseSchema],
    summary="Create Semester",
    tags=["Academic Platform"],
)
async def create_semester(
    organizationId: str,
    payload: SemesterCreateSchema,
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:write")),
):
    res = await service.create_semester(organizationId, payload.model_dump(by_alias=True))
    await _audit(res.organization_id, "semester.created", {"id": res.semester_id, "number": res.number})
    return APIResponse(success=True, message="Semester created successfully.", data=res)


@router.get(
    "/organizations/{organizationId}/semesters",
    response_model=APIResponse[List[SemesterResponseSchema]],
    summary="List Semesters",
    tags=["Academic Platform"],
)
async def list_semesters(
    organizationId: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    sortBy: str = Query("number"),
    sortOrder: str = Query("asc"),
    status: Optional[str] = Query(None),
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(get_current_identity),
):
    filters = {}
    if status:
        filters["status"] = status
    items, total = await service.list_semesters(organizationId, skip, limit, sortBy, sortOrder, filters)
    return APIResponse(success=True, data=items, meta={"pagination": {"skip": skip, "limit": limit, "total": total}})


@router.post(
    "/organizations/{organizationId}/semesters/bulk",
    response_model=APIResponse[List[SemesterResponseSchema]],
    summary="Bulk Create Semesters",
    tags=["Academic Platform"],
)
async def bulk_create_semesters(
    organizationId: str,
    payload: List[SemesterCreateSchema] = Body(...),
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:write")),
):
    items = [p.model_dump(by_alias=True) for p in payload]
    res = await service.bulk_create_semesters(organizationId, items)
    return APIResponse(success=True, message=f"Bulk created {len(res)} Semesters.", data=res)


@router.get(
    "/organizations/{organizationId}/semesters/{id}",
    response_model=APIResponse[SemesterResponseSchema],
    summary="Get Semester by ID",
    tags=["Academic Platform"],
)
async def get_semester(
    organizationId: str,
    id: str,
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(get_current_identity),
):
    res = await service.get_semester(organizationId, id)
    return APIResponse(success=True, data=res)


@router.patch(
    "/organizations/{organizationId}/semesters/{id}",
    response_model=APIResponse[SemesterResponseSchema],
    summary="Update Semester",
    tags=["Academic Platform"],
)
async def update_semester(
    organizationId: str,
    id: str,
    payload: SemesterUpdateSchema,
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:write")),
):
    res = await service.update_semester(organizationId, id, payload.model_dump(exclude_unset=True))
    await _audit(res.organization_id, "semester.updated", {"id": id})
    return APIResponse(success=True, message="Semester updated successfully.", data=res)


@router.delete(
    "/organizations/{organizationId}/semesters/{id}",
    response_model=APIResponse[bool],
    summary="Delete Semester",
    tags=["Academic Platform"],
)
async def delete_semester(
    organizationId: str,
    id: str,
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:delete")),
):
    res = await service.get_semester(organizationId, id)
    await service.delete_semester(organizationId, id)
    await _audit(res.organization_id, "semester.deleted", {"id": id})
    return APIResponse(success=True, message="Semester soft deleted.", data=True)


# ============================================================================
# SECTIONS
# ============================================================================

@router.post(
    "/organizations/{organizationId}/sections",
    response_model=APIResponse[SectionResponseSchema],
    summary="Create Section",
    tags=["Academic Platform"],
)
async def create_section(
    organizationId: str,
    payload: SectionCreateSchema,
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:write")),
):
    res = await service.create_section(organizationId, payload.model_dump(by_alias=True))
    await _audit(res.organization_id, "section.created", {"id": res.section_id})
    return APIResponse(success=True, message="Section created successfully.", data=res)


@router.get(
    "/organizations/{organizationId}/sections",
    response_model=APIResponse[List[SectionResponseSchema]],
    summary="List Sections",
    tags=["Academic Platform"],
)
async def list_sections(
    organizationId: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    sortBy: str = Query("createdAt"),
    sortOrder: str = Query("asc"),
    branchId: Optional[str] = Query(None),
    semesterId: Optional[str] = Query(None),
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(get_current_identity),
):
    filters = {}
    if branchId:
        filters["branchId"] = branchId
    if semesterId:
        filters["semesterId"] = semesterId
    items, total = await service.list_sections(organizationId, skip, limit, sortBy, sortOrder, filters)
    return APIResponse(success=True, data=items, meta={"pagination": {"skip": skip, "limit": limit, "total": total}})


@router.post(
    "/organizations/{organizationId}/sections/bulk",
    response_model=APIResponse[List[SectionResponseSchema]],
    summary="Bulk Create Sections",
    tags=["Academic Platform"],
)
async def bulk_create_sections(
    organizationId: str,
    payload: List[SectionCreateSchema] = Body(...),
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:write")),
):
    items = [p.model_dump(by_alias=True) for p in payload]
    res = await service.bulk_create_sections(organizationId, items)
    return APIResponse(success=True, message=f"Bulk created {len(res)} Sections.", data=res)


@router.patch(
    "/organizations/{organizationId}/sections/bulk",
    response_model=APIResponse[bool],
    summary="Bulk Update Sections",
    tags=["Academic Platform"],
)
async def bulk_update_sections(
    organizationId: str,
    payload: List[SectionBulkUpdateSchema] = Body(...),
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:write")),
):
    items = [p.model_dump(exclude_unset=True, by_alias=True) for p in payload]
    await service.bulk_update_sections(organizationId, items)
    return APIResponse(success=True, message=f"Bulk updated {len(payload)} Sections.", data=True)


@router.delete(
    "/organizations/{organizationId}/sections/bulk",
    response_model=APIResponse[bool],
    summary="Bulk Delete Sections",
    tags=["Academic Platform"],
)
async def bulk_delete_sections(
    organizationId: str,
    payload: BulkDeletePayload = Body(...),
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:write")),
):
    await service.bulk_delete_sections(organizationId, payload.ids)
    return APIResponse(success=True, message=f"Bulk deleted {len(payload.ids)} Sections.", data=True)


@router.get(
    "/organizations/{organizationId}/sections/{id}",
    response_model=APIResponse[SectionResponseSchema],
    summary="Get Section by ID",
    tags=["Academic Platform"],
)
async def get_section(
    organizationId: str,
    id: str,
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(get_current_identity),
):
    res = await service.get_section(organizationId, id)
    return APIResponse(success=True, data=res)


@router.patch(
    "/organizations/{organizationId}/sections/{id}",
    response_model=APIResponse[SectionResponseSchema],
    summary="Update Section",
    tags=["Academic Platform"],
)
async def update_section(
    organizationId: str,
    id: str,
    payload: SectionUpdateSchema,
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:write")),
):
    res = await service.update_section(organizationId, id, payload.model_dump(exclude_unset=True, by_alias=True))
    await _audit(res.organization_id, "section.updated", {"id": id})
    return APIResponse(success=True, message="Section updated successfully.", data=res)


@router.delete(
    "/organizations/{organizationId}/sections/{id}",
    response_model=APIResponse[bool],
    summary="Delete Section",
    tags=["Academic Platform"],
)
async def delete_section(
    organizationId: str,
    id: str,
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:write")),
):
    res = await service.get_section(organizationId, id)
    await service.delete_section(organizationId, id)
    await _audit(res.organization_id, "section.deleted", {"id": id})
    return APIResponse(success=True, message="Section soft deleted.", data=True)


# ============================================================================
# COURSES
# ============================================================================

@router.post(
    "/organizations/{organizationId}/courses",
    response_model=APIResponse[CourseResponseSchema],
    summary="Create Course",
    tags=["Academic Platform"],
)
async def create_course(
    organizationId: str,
    payload: CourseCreateSchema,
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:write")),
):
    res = await service.create_course(organizationId, payload.model_dump(by_alias=True))
    await _audit(res.organization_id, "course.created", {"id": res.course_id, "code": res.course_code})
    return APIResponse(success=True, message="Course created successfully.", data=res)


@router.get(
    "/organizations/{organizationId}/courses",
    response_model=APIResponse[List[CourseResponseSchema]],
    summary="List Courses",
    tags=["Academic Platform"],
)
async def list_courses(
    organizationId: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    sortBy: str = Query("createdAt"),
    sortOrder: str = Query("asc"),
    programId: Optional[str] = Query(None),
    semester: Optional[str] = Query(None),
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(get_current_identity),
):
    filters = {}
    if programId:
        filters["programId"] = programId
    if semester:
        filters["semester"] = semester
    items, total = await service.list_courses(organizationId, skip, limit, sortBy, sortOrder, filters)
    return APIResponse(success=True, data=items, meta={"pagination": {"skip": skip, "limit": limit, "total": total}})


@router.post(
    "/organizations/{organizationId}/courses/bulk",
    response_model=APIResponse[List[CourseResponseSchema]],
    summary="Bulk Create Courses",
    tags=["Academic Platform"],
)
async def bulk_create_courses(
    organizationId: str,
    payload: List[CourseCreateSchema] = Body(...),
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:write")),
):
    items = [p.model_dump(by_alias=True) for p in payload]
    res = await service.bulk_create_courses(organizationId, items)
    return APIResponse(success=True, message=f"Bulk created {len(res)} Courses.", data=res)


@router.patch(
    "/organizations/{organizationId}/courses/bulk",
    response_model=APIResponse[bool],
    summary="Bulk Update Courses",
    tags=["Academic Platform"],
)
async def bulk_update_courses(
    organizationId: str,
    payload: List[CourseBulkUpdateSchema] = Body(...),
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:write")),
):
    items = [p.model_dump(exclude_unset=True, by_alias=True) for p in payload]
    await service.bulk_update_courses(organizationId, items)
    return APIResponse(success=True, message=f"Bulk updated {len(payload)} Courses.", data=True)


@router.delete(
    "/organizations/{organizationId}/courses/bulk",
    response_model=APIResponse[bool],
    summary="Bulk Delete Courses",
    tags=["Academic Platform"],
)
async def bulk_delete_courses(
    organizationId: str,
    payload: BulkDeletePayload = Body(...),
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:write")),
):
    await service.bulk_delete_courses(organizationId, payload.ids)
    return APIResponse(success=True, message=f"Bulk deleted {len(payload.ids)} Courses.", data=True)


@router.get(
    "/organizations/{organizationId}/courses/{id}",
    response_model=APIResponse[CourseResponseSchema],
    summary="Get Course by ID",
    tags=["Academic Platform"],
)
async def get_course(
    organizationId: str,
    id: str,
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(get_current_identity),
):
    res = await service.get_course(organizationId, id)
    return APIResponse(success=True, data=res)


@router.patch(
    "/organizations/{organizationId}/courses/{id}",
    response_model=APIResponse[CourseResponseSchema],
    summary="Update Course",
    tags=["Academic Platform"],
)
async def update_course(
    organizationId: str,
    id: str,
    payload: CourseUpdateSchema,
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:write")),
):
    res = await service.update_course(organizationId, id, payload.model_dump(exclude_unset=True, by_alias=True))
    await _audit(res.organization_id, "course.updated", {"id": id})
    return APIResponse(success=True, message="Course updated successfully.", data=res)


@router.delete(
    "/organizations/{organizationId}/courses/{id}",
    response_model=APIResponse[bool],
    summary="Delete Course",
    tags=["Academic Platform"],
)
async def delete_course(
    organizationId: str,
    id: str,
    service: AcademicService = Depends(get_academic_service),
    _: Any = Depends(check_permission("academic:write")),
):
    res = await service.get_course(organizationId, id)
    await service.delete_course(organizationId, id)
    await _audit(res.organization_id, "course.deleted", {"id": id})
    return APIResponse(success=True, message="Course soft deleted.", data=True)
