from fastapi import APIRouter, Depends, Query, Path, status, Body
from typing import List, Optional, Any
from datetime import datetime

from app.schemas.schemas import APIResponse
from app.schemas.capability_schemas import (
    CapabilityCreateSchema, CapabilityUpdateSchema, CapabilityResponseSchema
)
from app.services.capability import CapabilityService, get_capability_service
from app.core.database import get_db

router = APIRouter()

async def log_audit(org_id: Any, action: str, details: dict):
    db = get_db()
    audit_log = {
        "organizationId": org_id,
        "action": action,
        "timestamp": datetime.utcnow(),
        "performedBy": "system",
        "details": details
    }
    await db["audit_logs"].insert_one(audit_log)

@router.post(
    "/seed",
    response_model=APIResponse[List[CapabilityResponseSchema]],
    summary="Seed default capabilities for an organization"
)
async def seed_capabilities(
    organizationId: str = Query(..., description="Organization ID to seed default capabilities for"),
    service: CapabilityService = Depends(get_capability_service)
):
    res = await service.seed_default_capabilities(organizationId)
    if res:
        await log_audit(res[0].organization_id, "capabilities_seeded", {"count": len(res)})
    return APIResponse(success=True, message=f"Seeded {len(res)} default capabilities.", data=res)

@router.get(
    "",
    response_model=APIResponse[List[CapabilityResponseSchema]],
    summary="List Organization Capabilities"
)
async def list_capabilities(
    organizationId: str = Query(..., description="Active Organization ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    sortBy: str = Query("createdAt"),
    sortOrder: str = Query("asc"),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    enabled: Optional[bool] = Query(None),
    installed: Optional[bool] = Query(None),
    service: CapabilityService = Depends(get_capability_service)
):
    filters = {}
    if category:
        filters["category"] = category
    if status:
        filters["status"] = status
    if enabled is not None:
        filters["enabled"] = enabled
    if installed is not None:
        filters["installed"] = installed

    items, total = await service.list_capabilities(organizationId, skip, limit, sortBy, sortOrder, filters)
    return APIResponse(
        success=True,
        data=items,
        meta={"pagination": {"skip": skip, "limit": limit, "total": total}}
    )

@router.get(
    "/categories",
    response_model=APIResponse[List[str]],
    summary="List Capability Categories"
)
async def list_categories():
    from app.models.org_engine.capability import CapabilityCategory
    categories = [cat.value for cat in CapabilityCategory]
    return APIResponse(success=True, data=categories)

@router.get(
    "/installed",
    response_model=APIResponse[List[CapabilityResponseSchema]],
    summary="List Installed Capabilities"
)
async def list_installed_capabilities(
    organizationId: str = Query(..., description="Active Organization ID"),
    service: CapabilityService = Depends(get_capability_service)
):
    items = await service.list_installed(organizationId)
    return APIResponse(success=True, data=items)

@router.get(
    "/enabled",
    response_model=APIResponse[List[CapabilityResponseSchema]],
    summary="List Enabled Capabilities"
)
async def list_enabled_capabilities(
    organizationId: str = Query(..., description="Active Organization ID"),
    service: CapabilityService = Depends(get_capability_service)
):
    items = await service.list_enabled(organizationId)
    return APIResponse(success=True, data=items)

@router.post(
    "",
    response_model=APIResponse[CapabilityResponseSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Create Capability"
)
async def create_capability(
    payload: CapabilityCreateSchema,
    service: CapabilityService = Depends(get_capability_service)
):
    res = await service.create_capability(payload.organizationId, payload.model_dump(by_alias=False))
    await log_audit(res.organization_id, "capability_created", {"capabilityId": res.capability_id, "slug": res.slug})
    return APIResponse(success=True, message="Capability registered successfully.", data=res)

@router.get(
    "/{id}",
    response_model=APIResponse[CapabilityResponseSchema],
    summary="Get Capability by ID"
)
async def get_capability(
    id: str,
    organizationId: str = Query(..., description="Active Organization ID"),
    service: CapabilityService = Depends(get_capability_service)
):
    res = await service.get_capability(organizationId, id)
    return APIResponse(success=True, data=res)

@router.patch(
    "/{id}",
    response_model=APIResponse[CapabilityResponseSchema],
    summary="Update Capability"
)
async def update_capability(
    id: str,
    payload: CapabilityUpdateSchema,
    organizationId: str = Query(..., description="Active Organization ID"),
    service: CapabilityService = Depends(get_capability_service)
):
    res = await service.update_capability(organizationId, id, payload.model_dump(exclude_unset=True, by_alias=False))
    await log_audit(res.organization_id, "capability_updated", {"capabilityId": id})
    return APIResponse(success=True, message="Capability updated successfully.", data=res)

@router.delete(
    "/{id}",
    response_model=APIResponse[bool],
    summary="Delete Capability"
)
async def delete_capability(
    id: str,
    organizationId: str = Query(..., description="Active Organization ID"),
    service: CapabilityService = Depends(get_capability_service)
):
    res = await service.get_capability(organizationId, id)
    org_id = res.organization_id
    await service.delete_capability(organizationId, id)
    await log_audit(org_id, "capability_deleted", {"capabilityId": id})
    return APIResponse(success=True, message="Capability deleted successfully.", data=True)

@router.post(
    "/{id}/enable",
    response_model=APIResponse[CapabilityResponseSchema],
    summary="Enable Capability"
)
async def enable_capability(
    id: str,
    organizationId: str = Query(..., description="Active Organization ID"),
    service: CapabilityService = Depends(get_capability_service)
):
    res = await service.enable_capability(organizationId, id)
    await log_audit(res.organization_id, "capability_enabled", {"capabilityId": id, "slug": res.slug})
    return APIResponse(success=True, message="Capability enabled successfully.", data=res)

@router.post(
    "/{id}/disable",
    response_model=APIResponse[CapabilityResponseSchema],
    summary="Disable Capability"
)
async def disable_capability(
    id: str,
    organizationId: str = Query(..., description="Active Organization ID"),
    service: CapabilityService = Depends(get_capability_service)
):
    res = await service.disable_capability(organizationId, id)
    await log_audit(res.organization_id, "capability_disabled", {"capabilityId": id, "slug": res.slug})
    return APIResponse(success=True, message="Capability disabled successfully.", data=res)
