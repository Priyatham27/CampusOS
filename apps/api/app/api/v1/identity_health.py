from fastapi import APIRouter, Depends
from apps.api.app.schemas.schemas import APIResponse
from apps.api.app.services.identity_health import IdentityHealthService, get_identity_health_service

router = APIRouter()

@router.get("/health", response_model=APIResponse, summary="Identity Subsystem Health check")
async def identity_subsystem_health(
    health_service: IdentityHealthService = Depends(get_identity_health_service)
):
    """
    Runs dynamic diagnostics across MongoDB connection, Redis cache state,
    session stores, configuration manager, and active authorization models.
    """
    health_report = await health_service.get_health_status()
    return APIResponse(
        success=True,
        message="Identity Subsystem Diagnostics completed successfully.",
        data=health_report
    )
