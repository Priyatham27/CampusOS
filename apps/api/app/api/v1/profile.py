from fastapi import APIRouter, Depends, status, UploadFile, File
from typing import Dict, Any

from apps.api.app.core.identity_context import IdentityContext, get_current_identity
from apps.api.app.schemas.schemas import APIResponse
from apps.api.app.schemas.user_schemas import ProfileResponseSchema, ProfileUpdateSchema
from apps.api.app.services.profile import ProfileService
from apps.api.app.services.avatar import AvatarService

router = APIRouter()

def get_profile_service() -> ProfileService:
    return ProfileService()

def get_avatar_service() -> AvatarService:
    return AvatarService()

@router.get("/me", response_model=APIResponse[ProfileResponseSchema], summary="Retrieve personal profile")
async def get_my_profile(
    context: IdentityContext = Depends(get_current_identity),
    profile_service: ProfileService = Depends(get_profile_service)
):
    profile = await profile_service.get_profile_by_user_id(context.user.id)
    res = ProfileResponseSchema.model_validate(profile)
    return APIResponse(
        success=True,
        message="Personal profile retrieved successfully.",
        data=res
    )

@router.patch("/me", response_model=APIResponse[ProfileResponseSchema], summary="Update personal profile")
async def update_my_profile(
    payload: ProfileUpdateSchema,
    context: IdentityContext = Depends(get_current_identity),
    profile_service: ProfileService = Depends(get_profile_service)
):
    update_dict = payload.model_dump(exclude_unset=True)
    profile = await profile_service.update_profile_by_user_id(
        user_id=context.user.id,
        update_data=update_dict,
        current_user=context.user
    )
    res = ProfileResponseSchema.model_validate(profile)
    return APIResponse(
        success=True,
        message="Personal profile updated successfully.",
        data=res
    )

@router.post("/avatar", response_model=APIResponse[Dict[str, Any]], summary="Upload personal avatar picture")
async def upload_my_avatar(
    file: UploadFile = File(...),
    context: IdentityContext = Depends(get_current_identity),
    profile_service: ProfileService = Depends(get_profile_service),
    avatar_service: AvatarService = Depends(get_avatar_service)
):
    # Upload and save avatar
    avatar_url = await avatar_service.upload_avatar(file)

    # Save reference in profile
    await profile_service.update_profile_by_user_id(
        user_id=context.user.id,
        update_data={"avatar": avatar_url},
        current_user=context.user
    )

    return APIResponse(
        success=True,
        message="Avatar uploaded and profile updated successfully.",
        data={"url": avatar_url}
    )
