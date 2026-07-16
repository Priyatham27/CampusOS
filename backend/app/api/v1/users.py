from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from typing import List, Optional, Dict, Any
from beanie import PydanticObjectId

from app.core.identity_context import IdentityContext, get_current_identity
# Instead of buggy requires_permission from auth.py, we evaluate resolved context permissions directly
def check_permission(required_permission: str):
    async def dependency(context: IdentityContext = Depends(get_current_identity)) -> None:
        if "super-admin" in context.active_roles:
            return
        if required_permission not in context.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required privilege: {required_permission}"
            )
    return dependency

from app.models.identity.user import User, Profile, StudentProfile, FacultyProfile, AdminProfile, AccountType
from app.models.identity.rbac import Role, UserRole
from app.schemas.schemas import APIResponse
from app.schemas.user_schemas import (
    UserCreateSchema,
    UserUpdateSchema,
    UserResponseSchema,
    ProfileResponseSchema,
    AcademicAffiliationSchema,
    BulkStatusUpdateSchema,
    BulkRolesUpdateSchema,
    BulkImportReport
)
from app.services.user import UserService
from app.services.user_search import UserSearchService
from app.services.bulk_import import BulkImportService

router = APIRouter()

def get_user_service() -> UserService:
    return UserService()

def get_search_service() -> UserSearchService:
    return UserSearchService()

def get_bulk_service() -> BulkImportService:
    return BulkImportService()

async def build_user_response(user: User) -> UserResponseSchema:
    """Helper method to construct complete response envelope for a user entity."""
    profile = await Profile.find_one(Profile.user_id == user.id, Profile.is_deleted == False)
    profile_schema = ProfileResponseSchema.model_validate(profile) if profile else None

    user_roles = await UserRole.find(UserRole.user_id == user.id).to_list()
    role_ids = [ur.role_id for ur in user_roles]
    roles = await Role.find({"_id": {"$in": role_ids}, "isDeleted": False}).to_list()
    role_slugs = [r.slug for r in roles]

    affiliation = None
    if user.account_type == AccountType.STUDENT:
        sp = await StudentProfile.find_one(StudentProfile.user_id == user.id, StudentProfile.is_deleted == False)
        if sp:
            affiliation = AcademicAffiliationSchema(
                rollNumber=sp.roll_number,
                departmentId=str(sp.department_id),
                programId=str(sp.program_id),
                branchId=str(sp.branch_id),
                semesterId=str(sp.semester_id),
                sectionId=str(sp.section_id),
                batch=sp.batch,
                admissionYear=sp.admission_year,
                graduationYear=sp.graduation_year
            )
    elif user.account_type == AccountType.FACULTY:
        fp = await FacultyProfile.find_one(FacultyProfile.user_id == user.id, FacultyProfile.is_deleted == False)
        if fp:
            affiliation = AcademicAffiliationSchema(
                employeeId=fp.employee_id,
                designation=fp.designation,
                departmentId=str(fp.department_id),
                qualification=fp.qualification
            )
    elif user.account_type in (AccountType.ADMIN, AccountType.SUPERADMIN):
        ap = await AdminProfile.find_one(AdminProfile.user_id == user.id, AdminProfile.is_deleted == False)
        if ap:
            affiliation = AcademicAffiliationSchema(
                designation=ap.designation,
                notes=ap.notes
            )

    return UserResponseSchema(
        id=str(user.id),
        userId=user.user_id,
        organizationId=str(user.organization_id),
        username=user.username,
        email=user.email,
        status=user.status,
        accountType=user.account_type,
        emailVerified=user.email_verified,
        phoneVerified=user.phone_verified,
        mfaEnabled=user.mfa_enabled,
        profile=profile_schema,
        roles=role_slugs,
        academicAffiliation=affiliation,
        createdAt=user.created_at,
        updatedAt=user.updated_at,
        lastLogin=user.last_login
    )

@router.post("", response_model=APIResponse[UserResponseSchema], status_code=status.HTTP_201_CREATED, summary="Create platform user")
async def create_user(
    payload: UserCreateSchema,
    context: IdentityContext = Depends(get_current_identity),
    user_service: UserService = Depends(get_user_service),
    _: None = Depends(check_permission("users:manage"))
):
    # Pass dict representation to service for ingestion
    user_dict = payload.model_dump()
    user = await user_service.create_user(
        org_id_str=str(context.organization.id),
        data=user_dict,
        current_user=context.user
    )
    res = await build_user_response(user)
    return APIResponse(
        success=True,
        message="User created successfully.",
        data=res
    )

@router.get("/search", response_model=APIResponse[List[UserResponseSchema]], summary="Search/filter users")
async def search_users(
    query: Optional[str] = Query(None, alias="query"),
    status: Optional[str] = Query(None),
    account_type: Optional[str] = Query(None, alias="accountType"),
    role_id: Optional[str] = Query(None, alias="roleId"),
    role_slug: Optional[str] = Query(None, alias="roleSlug"),
    department_id: Optional[str] = Query(None, alias="departmentId"),
    program_id: Optional[str] = Query(None, alias="programId"),
    branch_id: Optional[str] = Query(None, alias="branchId"),
    semester_id: Optional[str] = Query(None, alias="semesterId"),
    section_id: Optional[str] = Query(None, alias="sectionId"),
    batch: Optional[str] = Query(None),
    sort_by: str = Query("createdAt", alias="sortBy"),
    sort_order: str = Query("asc", alias="sortOrder"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    context: IdentityContext = Depends(get_current_identity),
    search_service: UserSearchService = Depends(get_search_service),
    _: None = Depends(check_permission("users:read"))
):
    filters = {
        "status": status,
        "accountType": account_type,
        "roleId": role_id,
        "roleSlug": role_slug,
        "departmentId": department_id,
        "programId": program_id,
        "branchId": branch_id,
        "semesterId": semester_id,
        "sectionId": section_id,
        "batch": batch
    }
    
    users, total = await search_service.search_users(
        org_id=context.organization.id,
        query_str=query,
        filters=filters,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=skip,
        limit=limit
    )

    data = [await build_user_response(u) for u in users]
    return APIResponse(
        success=True,
        message="Users search completed.",
        data=data,
        meta={"total": total, "skip": skip, "limit": limit}
    )

@router.get("", response_model=APIResponse[List[UserResponseSchema]], summary="List organization users")
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    sort_by: str = Query("createdAt", alias="sortBy"),
    sort_order: str = Query("asc", alias="sortOrder"),
    status: Optional[str] = Query(None),
    account_type: Optional[str] = Query(None, alias="accountType"),
    context: IdentityContext = Depends(get_current_identity),
    user_service: UserService = Depends(get_user_service),
    _: None = Depends(check_permission("users:read"))
):
    filters = {}
    if status:
        filters["status"] = status
    if account_type:
        filters["accountType"] = account_type

    users = await user_service.user_repo.list(
        org_id=context.organization.id,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
        filters=filters
    )
    total = await user_service.user_repo.count(
        org_id=context.organization.id,
        filters=filters
    )
    
    data = [await build_user_response(u) for u in users]
    return APIResponse(
        success=True,
        message="Retrieve users completed.",
        data=data,
        meta={"total": total, "skip": skip, "limit": limit}
    )



@router.post("/bulk-import", response_model=APIResponse[BulkImportReport], summary="Bulk import users from CSV")
async def bulk_import_users(
    preview: bool = Query(False),
    file: UploadFile = File(...),
    context: IdentityContext = Depends(get_current_identity),
    bulk_service: BulkImportService = Depends(get_bulk_service),
    _: None = Depends(check_permission("users:manage"))
):
    contents = await file.read()
    csv_str = contents.decode("utf-8")
    report = await bulk_service.import_users_csv(
        org_id_str=str(context.organization.id),
        csv_content=csv_str,
        preview=preview,
        current_user=context.user
    )
    return APIResponse(
        success=True,
        message="Bulk CSV import execution complete." if not preview else "Bulk CSV import preview report generated.",
        data=BulkImportReport(**report)
    )

@router.patch("/bulk-status", response_model=APIResponse[Dict[str, Any]], summary="Bulk update user status")
async def bulk_update_status(
    payload: BulkStatusUpdateSchema,
    context: IdentityContext = Depends(get_current_identity),
    user_service: UserService = Depends(get_user_service),
    _: None = Depends(check_permission("users:manage"))
):
    result = await user_service.bulk_status_change(
        org_id_str=str(context.organization.id),
        user_ids=payload.user_ids,
        status=payload.status,
        current_user=context.user,
        reason=payload.reason
    )
    return APIResponse(
        success=True,
        message="Bulk user status update executed.",
        data=result
    )

@router.patch("/bulk-roles", response_model=APIResponse[Dict[str, Any]], summary="Bulk assign user roles")
async def bulk_assign_roles(
    payload: BulkRolesUpdateSchema,
    context: IdentityContext = Depends(get_current_identity),
    user_service: UserService = Depends(get_user_service),
    _: None = Depends(check_permission("users:manage"))
):
    if payload.action not in ("add", "remove", "replace"):
        raise HTTPException(
            status_code=400,
            detail="Invalid action parameter. Must be one of: add, remove, replace."
        )

    result = await user_service.bulk_role_assignment(
        org_id_str=str(context.organization.id),
        user_ids=payload.user_ids,
        role_ids=payload.role_ids,
        action=payload.action,
        current_user=context.user
    )
    return APIResponse(
        success=True,
        message="Bulk user roles mapping update executed.",
        data=result
    )

# =====================================================================
# DYNAMIC USER PATH ENDPOINTS (must be at the bottom to prevent conflicts)
# =====================================================================

@router.get("/{userId}", response_model=APIResponse[UserResponseSchema], summary="Get user details")
async def get_user(
    userId: str,
    context: IdentityContext = Depends(get_current_identity),
    user_service: UserService = Depends(get_user_service),
    _: None = Depends(check_permission("users:read"))
):
    user = await user_service.get_user_details(str(context.organization.id), userId)
    res = await build_user_response(user)
    return APIResponse(
        success=True,
        message="User details resolved.",
        data=res
    )

@router.patch("/{userId}", response_model=APIResponse[UserResponseSchema], summary="Update user account")
async def update_user(
    userId: str,
    payload: UserUpdateSchema,
    context: IdentityContext = Depends(get_current_identity),
    user_service: UserService = Depends(get_user_service),
    _: None = Depends(check_permission("users:manage"))
):
    update_dict = payload.model_dump(exclude_unset=True)
    user = await user_service.update_user(
        org_id_str=str(context.organization.id),
        user_id_str=userId,
        update_data=update_dict,
        current_user=context.user
    )
    res = await build_user_response(user)
    return APIResponse(
        success=True,
        message="User updated successfully.",
        data=res
    )

@router.delete("/{userId}", response_model=APIResponse[None], summary="Soft delete user account")
async def delete_user(
    userId: str,
    context: IdentityContext = Depends(get_current_identity),
    user_service: UserService = Depends(get_user_service),
    _: None = Depends(check_permission("users:manage"))
):
    await user_service.soft_delete_user(
        org_id_str=str(context.organization.id),
        user_id_str=userId,
        current_user=context.user
    )
    return APIResponse(
        success=True,
        message="User logical deactivation completed successfully.",
        data=None
    )
