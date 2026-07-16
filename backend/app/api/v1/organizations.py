from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional

from app.schemas.schemas import APIResponse
from app.schemas.org_schemas import (
    OrganizationCreateSchema,
    OrganizationUpdateSchema,
    OrganizationResponseSchema
)
from app.services.organization import OrganizationService, get_organization_service

router = APIRouter()

@router.post(
    "",
    response_model=APIResponse[OrganizationResponseSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Organization",
    response_description="Enveloped newly created organization with default seeds loaded."
)
async def create_organization(
    payload: OrganizationCreateSchema,
    service: OrganizationService = Depends(get_organization_service)
):
    """
    Creates a white-labeled institutional tenant (Organization).
    Automatically seeds dynamic theme branding config, feature-flags, default modules registries,
    and checks conflicts inside a transaction context.
    """
    org = await service.create_organization(payload.model_dump(by_alias=False))
    return {
        "success": True,
        "message": "Organization created successfully.",
        "data": OrganizationResponseSchema.model_validate(org),
        "meta": {},
        "errors": []
    }

@router.get(
    "",
    response_model=APIResponse[List[OrganizationResponseSchema]],
    summary="Retrieve paginated list of Organizations",
    response_description="Paginated lists of active organizations matching search and filter parameters."
)
async def list_organizations(
    page: int = Query(default=1, ge=1, description="Page index (1-based)"),
    limit: int = Query(default=10, ge=1, le=100, description="Page limits size"),
    sort_by: str = Query(default="createdAt", description="Attribute key to sort by"),
    sort_order: str = Query(default="asc", description="Sort directions: asc or desc"),
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter organizations by active status"),
    university_id: Optional[str] = Query(default=None, alias="universityId", description="Filter by parent University ID"),
    q: Optional[str] = Query(default=None, description="Fuzzy name or keyword search string query"),
    service: OrganizationService = Depends(get_organization_service)
):
    """
    Query system-wide active organizations.
    Supports query pagination, custom attribute sorting, and dynamic filters.
    """
    skip = (page - 1) * limit
    
    # Handle fuzzy search vs listing query paths
    if q:
        orgs = await service.search_organizations(query_str=q, skip=skip, limit=limit)
        total = len(orgs)  # Simplify total for direct search results
    else:
        filters = {}
        if status_filter:
            filters["status"] = status_filter
        if university_id:
            filters["university_id"] = university_id
            
        orgs, total = await service.list_organizations(
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            filters=filters
        )

    validated_orgs = [OrganizationResponseSchema.model_validate(o) for o in orgs]
    
    return {
        "success": True,
        "message": "Organizations list loaded successfully.",
        "data": validated_orgs,
        "meta": {
            "page": page,
            "limit": limit,
            "total": total,
            "count": len(validated_orgs)
        },
        "errors": []
    }

@router.get(
    "/{organizationId}",
    response_model=APIResponse[OrganizationResponseSchema],
    summary="Retrieve single Organization",
    response_description="Detailed profile of the organization."
)
async def get_organization(
    organizationId: str,
    service: OrganizationService = Depends(get_organization_service)
):
    """Retrieve details of an active Organization by its unique custom identifier (e.g. ORG_000001)."""
    org = await service.get_organization(organizationId)
    return {
        "success": True,
        "message": "Organization details loaded.",
        "data": OrganizationResponseSchema.model_validate(org),
        "meta": {},
        "errors": []
    }

@router.patch(
    "/{organizationId}",
    response_model=APIResponse[OrganizationResponseSchema],
    summary="Partially update an Organization",
    response_description="Detailed profile of the modified organization."
)
async def update_organization(
    organizationId: str,
    payload: OrganizationUpdateSchema,
    service: OrganizationService = Depends(get_organization_service)
):
    """
    Applies partial modifications to branding or metadata parameters of an organization.
    Ensures name conflicts and structural integrity validations are run beforehand.
    """
    # Exclude unset fields from request payload
    update_data = payload.model_dump(exclude_unset=True, by_alias=False)
    org = await service.update_organization(organizationId, update_data)
    return {
        "success": True,
        "message": "Organization updated successfully.",
        "data": OrganizationResponseSchema.model_validate(org),
        "meta": {},
        "errors": []
    }

@router.delete(
    "/{organizationId}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete an Organization"
)
async def delete_organization(
    organizationId: str,
    service: OrganizationService = Depends(get_organization_service)
):
    """
    Soft deletes an organization from the active databases list.
    No hard removal is performed; flags the record status as deleted.
    """
    await service.delete_organization(organizationId)

@router.get(
    "/slug/{slug}",
    response_model=APIResponse[OrganizationResponseSchema],
    summary="Retrieve Organization by Slug",
    response_description="Detailed profile of the organization."
)
async def get_organization_by_slug(
    slug: str,
    service: OrganizationService = Depends(get_organization_service)
):
    """Retrieve organization details by unique slug."""
    org = await service.repo.find_by_slug(slug)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization with slug '{slug}' not found."
        )
    return {
        "success": True,
        "message": "Organization resolved by slug.",
        "data": OrganizationResponseSchema.model_validate(org),
        "meta": {},
        "errors": []
    }
