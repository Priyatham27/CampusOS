from fastapi import APIRouter, Depends, status, Path
from typing import List

from app.core.identity_context import IdentityContext, get_current_identity
from app.schemas.schemas import APIResponse
from app.schemas.authorization_schemas import (
    PermissionCreate,
    PermissionResponse,
    PermissionUpdate
)
from app.services.authorization import AuthorizationService
from app.repositories.authorization import AuthorizationRepository

router = APIRouter()

def get_auth_service() -> AuthorizationService:
    return AuthorizationService()

@router.get(
    "",
    response_model=APIResponse[List[PermissionResponse]],
    summary="List all system permissions"
)
async def list_permissions(
    context: IdentityContext = Depends(get_current_identity),
    repo: AuthorizationRepository = Depends(AuthorizationRepository)
):
    perms = await repo.list_permissions()
    responses = [PermissionResponse.model_validate(p) for p in perms]
    return APIResponse(
        success=True,
        message="System permissions resolved successfully.",
        data=responses
    )

@router.post(
    "",
    response_model=APIResponse[PermissionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create system permission"
)
async def create_permission(
    payload: PermissionCreate,
    context: IdentityContext = Depends(get_current_identity),
    service: AuthorizationService = Depends(get_auth_service)
):
    perm = await service.create_permission(
        module=payload.module,
        resource=payload.resource,
        action=payload.action,
        slug=payload.slug,
        description=payload.description
    )
    return APIResponse(
        success=True,
        message="Permission created successfully.",
        data=PermissionResponse.model_validate(perm)
    )

@router.patch(
    "/{permissionId}",
    response_model=APIResponse[PermissionResponse],
    summary="Update system permission details"
)
async def update_permission(
    payload: PermissionUpdate,
    permission_id: str = Path(..., alias="permissionId"),
    context: IdentityContext = Depends(get_current_identity),
    service: AuthorizationService = Depends(get_auth_service)
):
    perm = await service.update_permission(
        permission_id=permission_id,
        description=payload.description
    )
    return APIResponse(
        success=True,
        message="Permission updated successfully.",
        data=PermissionResponse.model_validate(perm)
    )

@router.delete(
    "/{permissionId}",
    response_model=APIResponse[None],
    summary="Delete system permission"
)
async def delete_permission(
    permission_id: str = Path(..., alias="permissionId"),
    context: IdentityContext = Depends(get_current_identity),
    service: AuthorizationService = Depends(get_auth_service)
):
    await service.delete_permission(permission_id)
    return APIResponse(
        success=True,
        message="Permission deleted successfully.",
        data=None
    )
