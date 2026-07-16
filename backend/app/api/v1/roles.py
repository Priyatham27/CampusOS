from fastapi import APIRouter, Depends, status, Path
from typing import List
from beanie import PydanticObjectId

from app.core.identity_context import IdentityContext, get_current_identity
from app.schemas.schemas import APIResponse
from app.schemas.authorization_schemas import (
    RoleCreate,
    RoleResponse,
    RoleUpdate,
    RolePermissionAssign,
    PermissionResponse
)
from app.services.authorization import AuthorizationService
from app.repositories.authorization import AuthorizationRepository

router = APIRouter()

def get_auth_service() -> AuthorizationService:
    return AuthorizationService()

@router.get(
    "",
    response_model=APIResponse[List[RoleResponse]],
    summary="List all organization roles"
)
async def list_roles(
    context: IdentityContext = Depends(get_current_identity),
    repo: AuthorizationRepository = Depends(AuthorizationRepository)
):
    roles = await repo.list_roles(context.organization.id)
    responses = [RoleResponse.model_validate(r) for r in roles]
    return APIResponse(
        success=True,
        message="Roles resolved successfully.",
        data=responses
    )

@router.post(
    "",
    response_model=APIResponse[RoleResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create organization role"
)
async def create_role(
    payload: RoleCreate,
    context: IdentityContext = Depends(get_current_identity),
    service: AuthorizationService = Depends(get_auth_service)
):
    role = await service.create_role(
        name=payload.name,
        slug=payload.slug,
        organization_id=context.organization.id,
        priority=payload.priority,
        description=payload.description
    )
    return APIResponse(
        success=True,
        message="Role created successfully.",
        data=RoleResponse.model_validate(role)
    )

@router.patch(
    "/{roleId}",
    response_model=APIResponse[RoleResponse],
    summary="Update organization role properties"
)
async def update_role(
    payload: RoleUpdate,
    role_id: str = Path(..., alias="roleId"),
    context: IdentityContext = Depends(get_current_identity),
    service: AuthorizationService = Depends(get_auth_service)
):
    role = await service.update_role(
        role_id=role_id,
        name=payload.name,
        priority=payload.priority,
        description=payload.description,
        org_id=context.organization.id
    )
    return APIResponse(
        success=True,
        message="Role updated successfully.",
        data=RoleResponse.model_validate(role)
    )

@router.delete(
    "/{roleId}",
    response_model=APIResponse[None],
    summary="Delete organization role"
)
async def delete_role(
    role_id: str = Path(..., alias="roleId"),
    context: IdentityContext = Depends(get_current_identity),
    service: AuthorizationService = Depends(get_auth_service)
):
    await service.delete_role(role_id, org_id=context.organization.id)
    return APIResponse(
        success=True,
        message="Role deleted successfully.",
        data=None
    )

@router.post(
    "/{roleId}/permissions",
    response_model=APIResponse[None],
    summary="Assign permission to role"
)
async def assign_permission_to_role(
    payload: RolePermissionAssign,
    role_id: str = Path(..., alias="roleId"),
    context: IdentityContext = Depends(get_current_identity),
    service: AuthorizationService = Depends(get_auth_service)
):
    await service.assign_permission_to_role(
        role_id_str=role_id,
        permission_id_str=payload.permission_id,
        org_id=context.organization.id,
        operator_roles=context.active_roles
    )
    return APIResponse(
        success=True,
        message="Permission assigned to role successfully.",
        data=None
    )

@router.delete(
    "/{roleId}/permissions/{permissionId}",
    response_model=APIResponse[None],
    summary="Revoke permission from role"
)
async def remove_permission_from_role(
    role_id: str = Path(..., alias="roleId"),
    permission_id: str = Path(..., alias="permissionId"),
    context: IdentityContext = Depends(get_current_identity),
    service: AuthorizationService = Depends(get_auth_service)
):
    await service.remove_permission_from_role(
        role_id_str=role_id,
        permission_id_str=permission_id,
        org_id=context.organization.id,
        operator_roles=context.active_roles
    )
    return APIResponse(
        success=True,
        message="Permission revoked from role successfully.",
        data=None
    )
