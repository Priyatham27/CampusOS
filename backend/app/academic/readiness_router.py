from fastapi import APIRouter, Depends, status
from typing import Any
from beanie import PydanticObjectId

from app.schemas.schemas import APIResponse
from app.core.identity_context import check_permission
from app.academic.health import AcademicHealthService
from app.academic.metrics import AcademicMetricsService

router = APIRouter()

@router.get(
    "/organizations/{organizationId}/academic/health",
    dependencies=[Depends(check_permission("academic:read"))],
    response_model=APIResponse
)
async def get_academic_health(organizationId: str):
    """
    Exposes unified diagnostic health checks for academic components,
    database connection, caching engine, and active configurations.
    """
    try:
        org_id = PydanticObjectId(organizationId)
    except Exception:
        return APIResponse(
            success=False,
            message="Invalid organization ID format.",
            data=None,
            meta={},
            errors=["InvalidOrganizationId"]
        )

    health_service = AcademicHealthService()
    health_data = await health_service.check_health(org_id)
    
    return APIResponse(
        success=True,
        message="Academic Platform health diagnostics fetched successfully.",
        data=health_data,
        meta={},
        errors=[]
    )

@router.get(
    "/organizations/{organizationId}/academic/metrics",
    dependencies=[Depends(check_permission("academic:read"))],
    response_model=APIResponse
)
async def get_academic_metrics(organizationId: str):
    """
    Exposes performance metrics, resolver latency statistics, 
    and cache hit/miss ratio counters.
    """
    metrics = AcademicMetricsService.get_metrics()
    return APIResponse(
        success=True,
        message="Academic Platform performance metrics statistics fetched successfully.",
        data=metrics,
        meta={},
        errors=[]
    )
