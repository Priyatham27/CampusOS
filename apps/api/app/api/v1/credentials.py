from fastapi import APIRouter, Depends, Query, Path, status, Request, Body
from typing import Optional
from apps.api.app.schemas.schemas import APIResponse
from apps.api.app.schemas.credential_schemas import (
    CredentialCreateSchema,
    PasswordChangeSchema,
    PasswordResetSchema,
    ForcePasswordResetSchema,
    CredentialResponseSchema,
    CredentialPatchSchema
)
from apps.api.app.services.credential import CredentialService, get_credential_service

router = APIRouter()

def get_client_ip(request: Request) -> Optional[str]:
    """Helper to extract IP address from request headers or client details."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None

@router.post(
    "",
    response_model=APIResponse[CredentialResponseSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Create credential record for user"
)
async def create_credential(
    request: Request,
    payload: CredentialCreateSchema,
    service: CredentialService = Depends(get_credential_service)
):
    ip = get_client_ip(request)
    res = await service.create_credential(
        user_id_str=payload.user_id,
        password=payload.password,
        cred_type=payload.type,
        ip_address=ip
    )
    return APIResponse(
        success=True,
        message="Credential record created successfully.",
        data=CredentialResponseSchema.model_validate(res)
    )

@router.post(
    "/change-password",
    response_model=APIResponse[CredentialResponseSchema],
    summary="Change user password with verification"
)
async def change_password(
    request: Request,
    payload: PasswordChangeSchema,
    service: CredentialService = Depends(get_credential_service)
):
    ip = get_client_ip(request)
    res = await service.change_password(
        user_id_str=payload.user_id,
        current_password=payload.current_password,
        new_password=payload.new_password,
        ip_address=ip
    )
    return APIResponse(
        success=True,
        message="Password changed successfully.",
        data=CredentialResponseSchema.model_validate(res)
    )

@router.post(
    "/reset-password",
    response_model=APIResponse[CredentialResponseSchema],
    summary="Reset user password using token"
)
async def reset_password(
    request: Request,
    payload: PasswordResetSchema,
    service: CredentialService = Depends(get_credential_service)
):
    ip = get_client_ip(request)
    res = await service.reset_password(
        user_id_str=payload.user_id,
        token=payload.token,
        new_password=payload.new_password,
        ip_address=ip
    )
    return APIResponse(
        success=True,
        message="Password reset completed successfully.",
        data=CredentialResponseSchema.model_validate(res)
    )

@router.post(
    "/force-reset",
    response_model=APIResponse[CredentialResponseSchema],
    summary="Force password reset by administrator"
)
async def force_reset(
    request: Request,
    payload: ForcePasswordResetSchema,
    service: CredentialService = Depends(get_credential_service)
):
    ip = get_client_ip(request)
    res = await service.force_password_reset(
        user_id_str=payload.user_id,
        new_password=payload.new_password,
        ip_address=ip
    )
    return APIResponse(
        success=True,
        message="Force password reset completed successfully.",
        data=CredentialResponseSchema.model_validate(res)
    )

@router.get(
    "/{userId}",
    response_model=APIResponse[CredentialResponseSchema],
    summary="Retrieve credential configuration by userId"
)
async def get_credential(
    userId: str = Path(..., description="The user identifier (prefixed string or Beanie BSON string)"),
    service: CredentialService = Depends(get_credential_service)
):
    res = await service.get_credential_by_user(userId)
    return APIResponse(
        success=True,
        message="Credential details resolved.",
        data=CredentialResponseSchema.model_validate(res)
    )

@router.patch(
    "/{userId}",
    response_model=APIResponse[CredentialResponseSchema],
    summary="Modify generic credential settings and flags"
)
async def patch_credential(
    userId: str = Path(..., description="The user identifier"),
    payload: CredentialPatchSchema = Body(...),
    service: CredentialService = Depends(get_credential_service)
):
    res = await service.update_credential_fields(
        user_id_str=userId,
        update_data=payload.model_dump(by_alias=False, exclude_unset=True)
    )
    return APIResponse(
        success=True,
        message="Credential configurations updated successfully.",
        data=CredentialResponseSchema.model_validate(res)
    )
