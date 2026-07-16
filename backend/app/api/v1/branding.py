from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from typing import List, Dict, Any, Optional

from app.schemas.schemas import APIResponse
from app.schemas.branding_schemas import (
    BrandingUpdateSchema,
    BrandingResponseSchema,
    BrandingRevisionResponseSchema
)
from app.services.branding import BrandingService, get_branding_service

router = APIRouter(
    prefix="/organizations/{organizationId}/branding",
    tags=["Branding APIs"]
)

def make_branding_response(
    branding: Any, 
    service: BrandingService, 
    preview: bool = False
) -> Dict[str, Any]:
    """Helper to convert Beanie Branding document to response schema, embedding dynamic CSS/Tailwind variables."""
    data = branding.model_dump(by_alias=False)
    data["css_variables"] = service.generate_css_variables(branding, preview=preview)
    data["tailwind_tokens"] = service.generate_theme_tokens(branding, preview=preview)
    return data

@router.get(
    "",
    response_model=APIResponse[BrandingResponseSchema],
    summary="Retrieve Organization Branding",
    response_description="Returns branding details including dynamic CSS variables and Tailwind tokens."
)
async def get_branding(
    organizationId: str,
    preview: bool = Query(default=False, description="Overlay uncommitted draft changes if true"),
    service: BrandingService = Depends(get_branding_service)
):
    """Retrieve branding parameters for the specified organization."""
    branding = await service.get_branding(organizationId, preview=preview)
    return {
        "success": True,
        "message": "Branding configurations loaded successfully.",
        "data": make_branding_response(branding, service, preview=preview),
        "meta": {"previewMode": preview},
        "errors": []
    }

@router.patch(
    "",
    response_model=APIResponse[BrandingResponseSchema],
    summary="Partially Update Branding",
    response_description="Returns updated branding config."
)
async def update_branding(
    organizationId: str,
    payload: BrandingUpdateSchema,
    preview: bool = Query(default=False, description="Save changes into preview buffer without publishing if true"),
    service: BrandingService = Depends(get_branding_service)
):
    """
    Applies partial configuration changes to the branding configuration.
    If preview=True is passed, changes are buffered in draft config.
    """
    update_data = payload.model_dump(exclude_unset=True, by_alias=False)
    branding = await service.update_branding(
        organization_id_str=organizationId,
        update_data=update_data,
        preview=preview
    )
    return {
        "success": True,
        "message": "Branding preview buffered successfully." if preview else "Branding updated and published successfully.",
        "data": make_branding_response(branding, service, preview=preview),
        "meta": {"previewMode": preview},
        "errors": []
    }

@router.post(
    "/reset",
    response_model=APIResponse[BrandingResponseSchema],
    summary="Reset Branding Defaults",
    response_description="Returns default reset branding config."
)
async def reset_branding(
    organizationId: str,
    service: BrandingService = Depends(get_branding_service)
):
    """Resets all color palettes and design systems config to CampusOS standards."""
    branding = await service.reset_branding(organizationId)
    return {
        "success": True,
        "message": "Branding reset to CampusOS defaults successfully.",
        "data": make_branding_response(branding, service, preview=False),
        "meta": {},
        "errors": []
    }

@router.post(
    "/logo",
    response_model=APIResponse[BrandingResponseSchema],
    summary="Upload Logo Asset",
    response_description="Returns branding details with optimized logo URL."
)
async def upload_logo(
    organizationId: str,
    file: UploadFile = File(...),
    isDark: bool = Query(default=False, alias="isDark", description="Upload as dark theme logo variant if true"),
    service: BrandingService = Depends(get_branding_service)
):
    """Uploads a logo image to Cloudinary storage layer and updates configuration."""
    branding = await service.upload_logo(organizationId, file, is_dark=isDark)
    return {
        "success": True,
        "message": "Dark theme logo uploaded successfully." if isDark else "Institution logo uploaded successfully.",
        "data": make_branding_response(branding, service, preview=False),
        "meta": {},
        "errors": []
    }

@router.delete(
    "/logo",
    response_model=APIResponse[BrandingResponseSchema],
    summary="Delete Logo Asset",
    response_description="Returns branding details after logo removal."
)
async def delete_logo(
    organizationId: str,
    isDark: bool = Query(default=False, alias="isDark", description="Delete dark theme logo variant if true"),
    service: BrandingService = Depends(get_branding_service)
):
    """Soft deletes the logo setting the logo URL back to None."""
    branding = await service.delete_logo(organizationId, is_dark=isDark)
    return {
        "success": True,
        "message": "Dark theme logo removed successfully." if isDark else "Institution logo removed successfully.",
        "data": make_branding_response(branding, service, preview=False),
        "meta": {},
        "errors": []
    }

@router.post(
    "/banner",
    response_model=APIResponse[BrandingResponseSchema],
    summary="Upload Banner Asset",
    response_description="Returns branding details with banner URL."
)
async def upload_banner(
    organizationId: str,
    file: UploadFile = File(...),
    service: BrandingService = Depends(get_branding_service)
):
    """Uploads a landscape banner image (aspect ratio >= 2.0) and updates configuration."""
    branding = await service.upload_banner(organizationId, file)
    return {
        "success": True,
        "message": "Institution branding banner uploaded successfully.",
        "data": make_branding_response(branding, service, preview=False),
        "meta": {},
        "errors": []
    }

@router.get(
    "/history",
    response_model=APIResponse[List[BrandingRevisionResponseSchema]],
    summary="Retrieve Branding History Revisions",
    response_description="List of history snapshot records."
)
async def get_branding_history(
    organizationId: str,
    service: BrandingService = Depends(get_branding_service)
):
    """Returns a list of all historical branding configurations stored for this organization."""
    history = await service.get_branding_history(organizationId)
    validated_history = [BrandingRevisionResponseSchema.model_validate(h) for h in history]
    return {
        "success": True,
        "message": "Branding revision history loaded successfully.",
        "data": validated_history,
        "meta": {"count": len(validated_history)},
        "errors": []
    }

@router.post(
    "/rollback/{version}",
    response_model=APIResponse[BrandingResponseSchema],
    summary="Rollback Branding Configuration",
    response_description="Returns the branding configuration after rollback."
)
async def rollback_branding(
    organizationId: str,
    version: int,
    service: BrandingService = Depends(get_branding_service)
):
    """Restores branding parameters to the exact configuration saved under the specified history version."""
    branding = await service.rollback_branding(organizationId, version)
    return {
        "success": True,
        "message": f"Branding rolled back to version {version} successfully.",
        "data": make_branding_response(branding, service, preview=False),
        "meta": {},
        "errors": []
    }
