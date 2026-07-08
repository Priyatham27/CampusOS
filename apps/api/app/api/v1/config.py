from fastapi import APIRouter, Depends, Query, Path, status, Body
from typing import List, Optional, Any
from datetime import datetime

from apps.api.app.schemas.schemas import APIResponse
from apps.api.app.schemas.config_schemas import (
    ConfigurationCreateSchema, ConfigurationUpdateSchema, ConfigurationResponseSchema,
    FeatureFlagCreateSchema, FeatureFlagUpdateSchema, FeatureFlagResponseSchema,
    FeatureFlagEvaluationContext
)
from apps.api.app.services.config import ConfigurationService, get_config_service
from apps.api.app.core.database import get_db

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

# ==========================================
# CONFIGURATION ENDPOINTS
# ==========================================

@router.get(
    "/config",
    response_model=APIResponse[Any],
    summary="List configurations or resolve configuration hierarchy"
)
async def list_or_resolve_config(
    organizationId: Optional[str] = Query(None, description="Organization ID"),
    key: Optional[str] = Query(None, description="Configuration key"),
    resolve: bool = Query(False, description="Set to true to resolve configuration hierarchy"),
    module: Optional[str] = Query(None, description="Module scope filter/context"),
    userId: Optional[str] = Query(None, description="User scope filter/context"),
    environment: str = Query("PRODUCTION", description="Environment context"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    sortBy: str = Query("createdAt"),
    sortOrder: str = Query("asc"),
    scope: Optional[str] = Query(None),
    service: ConfigurationService = Depends(get_config_service)
):
    if resolve:
        if not key:
            return APIResponse(success=False, message="Key is required for configuration resolution.", status_code=400)
        res = await service.resolve_configuration(
            org_id_str=organizationId,
            key=key,
            environment=environment,
            module=module,
            user_id=userId
        )
        return APIResponse(success=True, data=res)
    else:
        filters = {}
        if scope:
            filters["scope"] = scope
        if environment:
            filters["environment"] = environment
        if module:
            filters["module"] = module
        if key:
            filters["key"] = key

        items, total = await service.cfg_repo.list(
            org_id=None, # List logic handles resolving system/global
            skip=skip,
            limit=limit,
            sort_by=sortBy,
            sort_order=sortOrder,
            filters=filters
        )
        if organizationId:
            org = await service._resolve_org(organizationId)
            items = await service.cfg_repo.list(
                org_id=org.id,
                skip=skip,
                limit=limit,
                sort_by=sortBy,
                sort_order=sortOrder,
                filters=filters
            )
            total = await service.cfg_repo.count(org_id=org.id, filters=filters)
        else:
            total = await service.cfg_repo.count(org_id=None, filters=filters)

        # Convert documents to schemas
        data = [ConfigurationResponseSchema.model_validate(item) for item in items]
        return APIResponse(
            success=True,
            data=data,
            meta={"pagination": {"skip": skip, "limit": limit, "total": total}}
        )

@router.get(
    "/config/{key}",
    response_model=APIResponse[ConfigurationResponseSchema],
    summary="Get Configuration by Key"
)
async def get_config(
    key: str,
    organizationId: Optional[str] = Query(None),
    environment: str = Query("PRODUCTION"),
    service: ConfigurationService = Depends(get_config_service)
):
    res = await service.get_config(organizationId, key, environment)
    return APIResponse(success=True, data=res)

@router.post(
    "/config",
    response_model=APIResponse[ConfigurationResponseSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Create Configuration"
)
async def create_config(
    payload: ConfigurationCreateSchema,
    service: ConfigurationService = Depends(get_config_service)
):
    res = await service.create_config(payload.organizationId, payload.model_dump(by_alias=False, exclude_unset=True))
    await log_audit(res.organization_id, "config_created", {"configId": res.config_id, "key": res.key, "scope": res.scope})
    return APIResponse(success=True, message="Configuration created successfully.", data=res)

@router.patch(
    "/config/{key}",
    response_model=APIResponse[ConfigurationResponseSchema],
    summary="Update Configuration"
)
async def update_config(
    key: str,
    payload: ConfigurationUpdateSchema,
    organizationId: Optional[str] = Query(None),
    environment: str = Query("PRODUCTION"),
    service: ConfigurationService = Depends(get_config_service)
):
    res = await service.update_config(organizationId, key, payload.model_dump(by_alias=False, exclude_unset=True), environment)
    await log_audit(res.organization_id, "config_updated", {"configId": res.config_id, "key": res.key})
    return APIResponse(success=True, message="Configuration updated successfully.", data=res)

@router.delete(
    "/config/{key}",
    response_model=APIResponse[bool],
    summary="Delete Configuration"
)
async def delete_config(
    key: str,
    organizationId: Optional[str] = Query(None),
    environment: str = Query("PRODUCTION"),
    service: ConfigurationService = Depends(get_config_service)
):
    # Resolve first to get org_id
    cfg = await service.get_config(organizationId, key, environment)
    org_id = cfg.organization_id
    await service.delete_config(organizationId, key, environment)
    await log_audit(org_id, "config_deleted", {"configId": cfg.config_id, "key": key})
    return APIResponse(success=True, message="Configuration deleted successfully.", data=True)


# ==========================================
# FEATURE FLAG ENDPOINTS
# ==========================================

@router.get(
    "/features",
    response_model=APIResponse[List[FeatureFlagResponseSchema]],
    summary="List Feature Flags"
)
async def list_features(
    organizationId: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    environment: Optional[str] = Query(None),
    enabled: Optional[bool] = Query(None),
    key: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    sortBy: str = Query("createdAt"),
    sortOrder: str = Query("asc"),
    service: ConfigurationService = Depends(get_config_service)
):
    filters = {}
    if category:
        filters["category"] = category
    if environment:
        filters["environment"] = environment
    if enabled is not None:
        filters["enabled"] = enabled
    if key:
        filters["key"] = key

    org_id = None
    if organizationId:
        org = await service._resolve_org(organizationId)
        org_id = org.id

    items = await service.flg_repo.list(org_id, skip, limit, sortBy, sortOrder, filters)
    total = await service.flg_repo.count(org_id, filters)
    
    data = [FeatureFlagResponseSchema.model_validate(item) for item in items]
    return APIResponse(
        success=True,
        data=data,
        meta={"pagination": {"skip": skip, "limit": limit, "total": total}}
    )

@router.get(
    "/features/{key}",
    response_model=APIResponse[FeatureFlagResponseSchema],
    summary="Get Feature Flag"
)
async def get_feature_flag(
    key: str,
    organizationId: Optional[str] = Query(None),
    environment: str = Query("PRODUCTION"),
    service: ConfigurationService = Depends(get_config_service)
):
    res = await service.get_feature_flag(organizationId, key, environment)
    return APIResponse(success=True, data=res)

@router.post(
    "/features",
    response_model=APIResponse[FeatureFlagResponseSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Create Feature Flag"
)
async def create_feature_flag(
    payload: FeatureFlagCreateSchema,
    service: ConfigurationService = Depends(get_config_service)
):
    res = await service.create_feature_flag(payload.organizationId, payload.model_dump(by_alias=False, exclude_unset=True))
    await log_audit(res.organization_id, "feature_flag_created", {"flagId": res.flag_id, "key": res.key})
    return APIResponse(success=True, message="Feature flag registered successfully.", data=res)

@router.patch(
    "/features/{key}",
    response_model=APIResponse[FeatureFlagResponseSchema],
    summary="Update Feature Flag"
)
async def update_feature_flag(
    key: str,
    payload: FeatureFlagUpdateSchema,
    organizationId: Optional[str] = Query(None),
    environment: str = Query("PRODUCTION"),
    service: ConfigurationService = Depends(get_config_service)
):
    res = await service.update_feature_flag(organizationId, key, payload.model_dump(by_alias=False, exclude_unset=True), environment)
    await log_audit(res.organization_id, "feature_flag_updated", {"flagId": res.flag_id, "key": res.key})
    return APIResponse(success=True, message="Feature flag updated successfully.", data=res)

@router.delete(
    "/features/{key}",
    response_model=APIResponse[bool],
    summary="Delete Feature Flag"
)
async def delete_feature_flag(
    key: str,
    organizationId: Optional[str] = Query(None),
    environment: str = Query("PRODUCTION"),
    service: ConfigurationService = Depends(get_config_service)
):
    flg = await service.get_feature_flag(organizationId, key, environment)
    org_id = flg.organization_id
    await service.delete_feature_flag(organizationId, key, environment)
    await log_audit(org_id, "feature_flag_deleted", {"flagId": flg.flag_id, "key": key})
    return APIResponse(success=True, message="Feature flag deleted successfully.", data=True)

@router.post(
    "/features/{key}/enable",
    response_model=APIResponse[FeatureFlagResponseSchema],
    summary="Enable Feature Flag"
)
async def enable_feature_flag(
    key: str,
    organizationId: Optional[str] = Query(None),
    environment: str = Query("PRODUCTION"),
    service: ConfigurationService = Depends(get_config_service)
):
    res = await service.enable_feature_flag(organizationId, key, environment)
    await log_audit(res.organization_id, "feature_flag_enabled", {"flagId": res.flag_id, "key": key})
    return APIResponse(success=True, message="Feature flag enabled successfully.", data=res)

@router.post(
    "/features/{key}/disable",
    response_model=APIResponse[FeatureFlagResponseSchema],
    summary="Disable Feature Flag"
)
async def disable_feature_flag(
    key: str,
    organizationId: Optional[str] = Query(None),
    environment: str = Query("PRODUCTION"),
    service: ConfigurationService = Depends(get_config_service)
):
    res = await service.disable_feature_flag(organizationId, key, environment)
    await log_audit(res.organization_id, "feature_flag_disabled", {"flagId": res.flag_id, "key": key})
    return APIResponse(success=True, message="Feature flag disabled successfully.", data=res)

@router.post(
    "/features/{key}/evaluate",
    response_model=APIResponse[bool],
    summary="Evaluate Feature Flag"
)
async def evaluate_feature_flag(
    key: str,
    context: FeatureFlagEvaluationContext,
    organizationId: Optional[str] = Query(None),
    service: ConfigurationService = Depends(get_config_service)
):
    res = await service.evaluate_feature_flag(organizationId, key, context.model_dump(by_alias=False))
    return APIResponse(success=True, data=res)
